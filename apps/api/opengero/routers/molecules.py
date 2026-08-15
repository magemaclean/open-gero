from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from ..chemistry import descriptors_from_smiles, parse_csv_rows, parse_sdf, parse_smiles, parse_smiles_table
from ..config import get_settings
from ..db import get_db
from ..deps import owned_project
from ..chemistry import params_hash
from ..models import Job, JobBatch, Molecule, MoleculeProperty, Project
from ..schemas import ImportReport, MoleculeIn, MoleculeOut, PropertiesOut
from ..tasks import enqueue_or_run

router = APIRouter(tags=["molecules"])

OPS = {
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
}


def _mol_out(mol: Molecule) -> MoleculeOut:
    props = None
    if mol.properties:
        p = mol.properties
        props = PropertiesOut(
            mw=p.mw,
            logp=p.logp,
            tpsa=p.tpsa,
            hbd=p.hbd,
            hba=p.hba,
            rotatable_bonds=p.rotatable_bonds,
            ring_count=p.ring_count,
            lipinski_pass=p.lipinski_pass,
            veber_pass=p.veber_pass,
            qed=p.qed,
            formula=mol.formula,
        )
    return MoleculeOut(
        id=mol.id,
        project_id=mol.project_id,
        name=mol.name,
        smiles_raw=mol.smiles_raw,
        canonical_smiles=mol.canonical_smiles,
        inchikey=mol.inchikey,
        formula=mol.formula,
        source=mol.source,
        source_row=mol.source_row,
        created_at=mol.created_at,
        deleted_at=mol.deleted_at,
        properties=props,
    )


def _apply_properties(db: Session, mol: Molecule) -> None:
    desc = descriptors_from_smiles(mol.canonical_smiles)
    if not desc:
        return
    from ..chemistry import fp_to_bytes, mol_from_smiles, morgan_fp

    rdkit_mol = mol_from_smiles(mol.canonical_smiles)
    props = db.get(MoleculeProperty, mol.id)
    if props is None:
        props = MoleculeProperty(molecule_id=mol.id)
        db.add(props)
    for key in (
        "mw",
        "logp",
        "tpsa",
        "hbd",
        "hba",
        "rotatable_bonds",
        "ring_count",
        "lipinski_pass",
        "veber_pass",
        "qed",
    ):
        setattr(props, key, desc[key])
    mol.formula = desc["formula"]
    if rdkit_mol is not None:
        props.fp_morgan = fp_to_bytes(morgan_fp(rdkit_mol))


def _upsert(db: Session, project_id: str, parsed, source: str) -> tuple[Molecule | None, str]:
    if parsed.error or not parsed.inchikey:
        return None, "error"
    existing = (
        db.query(Molecule)
        .filter(
            Molecule.project_id == project_id,
            Molecule.inchikey == parsed.inchikey,
            Molecule.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        if parsed.name and not existing.name:
            existing.name = parsed.name
        return existing, "duplicate"
    mol = Molecule(
        project_id=project_id,
        name=parsed.name,
        smiles_raw=parsed.smiles_raw,
        canonical_smiles=parsed.canonical_smiles,
        inchikey=parsed.inchikey,
        source=source,
        source_row=parsed.source_row,
    )
    db.add(mol)
    db.flush()
    return mol, "new"


@router.get("/api/projects/{project_id}/molecules", response_model=list[MoleculeOut])
def list_molecules(
    response: Response,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
    q: str | None = None,
    lipinski: bool | None = None,
    veber: bool | None = None,
    mw_max: float | None = None,
    mw_min: float | None = None,
    tpsa_max: float | None = None,
    logp_max: float | None = None,
    deleted: bool = False,
    limit: int = Query(50, le=2000),
    offset: int = 0,
) -> list[MoleculeOut]:
    query = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .outerjoin(MoleculeProperty, MoleculeProperty.molecule_id == Molecule.id)
        .filter(Molecule.project_id == project.id)
    )
    if deleted:
        query = query.filter(Molecule.deleted_at.is_not(None))
    else:
        query = query.filter(Molecule.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Molecule.name.ilike(like))
            | (Molecule.canonical_smiles.ilike(like))
            | (Molecule.inchikey.ilike(like))
        )
    if lipinski is not None:
        query = query.filter(MoleculeProperty.lipinski_pass.is_(lipinski))
    if veber is not None:
        query = query.filter(MoleculeProperty.veber_pass.is_(veber))
    if mw_max is not None:
        query = query.filter(MoleculeProperty.mw.is_not(None), MoleculeProperty.mw <= mw_max)
    if mw_min is not None:
        query = query.filter(MoleculeProperty.mw.is_not(None), MoleculeProperty.mw >= mw_min)
    if tpsa_max is not None:
        query = query.filter(MoleculeProperty.tpsa.is_not(None), MoleculeProperty.tpsa <= tpsa_max)
    if logp_max is not None:
        query = query.filter(MoleculeProperty.logp.is_not(None), MoleculeProperty.logp <= logp_max)
    total = query.count()
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
        response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    rows = query.order_by(Molecule.created_at.desc()).offset(offset).limit(limit).all()
    return [_mol_out(mol) for mol in rows]


@router.post("/api/projects/{project_id}/molecules", response_model=MoleculeOut, status_code=201)
def add_molecule(
    body: MoleculeIn,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
) -> MoleculeOut:
    parsed = parse_smiles(body.smiles, name=body.name)
    if parsed.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, parsed.error)
    mol, kind = _upsert(db, project.id, parsed, "editor")
    if mol is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not ingest molecule")
    if kind == "new":
        _apply_properties(db, mol)
    db.commit()
    db.refresh(mol)
    mol = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .filter(Molecule.id == mol.id)
        .one()
    )
    return _mol_out(mol)


@router.post("/api/projects/{project_id}/molecules/import", response_model=ImportReport)
async def import_molecules(
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    fmt: str = Form(default="smiles"),
    smiles_col: str = Form(default="smiles"),
    name_col: str | None = Form(default="name"),
) -> ImportReport:
    settings = get_settings()
    raw_text = text or ""
    raw_bytes = b""
    if file is not None:
        raw_bytes = await file.read()
        filename = (file.filename or "").lower()
        if filename.endswith(".sdf") or filename.endswith(".sd"):
            fmt = "sdf"
        elif filename.endswith(".csv"):
            fmt = "csv"
        elif filename.endswith(".smi") or filename.endswith(".smiles"):
            fmt = "smiles"
        if fmt != "sdf":
            raw_text = raw_bytes.decode("utf-8", errors="replace")
    if fmt == "sdf":
        parsed_rows = parse_sdf(raw_bytes)
    elif fmt == "csv":
        parsed_rows = parse_csv_rows(raw_text, smiles_col=smiles_col, name_col=name_col)
    else:
        parsed_rows = parse_smiles_table(raw_text)
    if len(parsed_rows) > settings.max_import_rows:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Import exceeds {settings.max_import_rows} row limit",
        )
    accepted = 0
    rejected = 0
    duplicates = 0
    errors: list[dict[str, Any]] = []
    new_ids: list[str] = []
    for parsed in parsed_rows:
        if parsed.error:
            rejected += 1
            errors.append({"row": parsed.source_row, "name": parsed.name, "error": parsed.error})
            continue
        mol, kind = _upsert(db, project.id, parsed, fmt)
        if kind == "duplicate":
            duplicates += 1
        elif kind == "new" and mol:
            accepted += 1
            new_ids.append(mol.id)
        else:
            rejected += 1
    db.commit()
    if new_ids and len(new_ids) <= settings.descriptor_inline_limit:
        for mid in new_ids:
            mol = db.get(Molecule, mid)
            if mol:
                _apply_properties(db, mol)
        db.commit()
    elif new_ids:
        job = Job(
            project_id=project.id,
            user_id=project.owner_id,
            type="descriptor_batch",
            status="queued",
            params_json={"source": "import"},
            params_hash=params_hash({"type": "descriptor_batch", "n": len(new_ids)}),
            total_items=len(new_ids),
        )
        db.add(job)
        db.flush()
        batch_size = settings.default_batch_size
        for i in range(0, len(new_ids), batch_size):
            chunk = new_ids[i : i + batch_size]
            db.add(JobBatch(job_id=job.id, index=i // batch_size, molecule_ids=chunk))
        db.commit()
        enqueue_or_run(job.id)
    return ImportReport(
        accepted=accepted,
        rejected=rejected,
        duplicates_merged=duplicates,
        errors=errors[:200],
        molecule_ids=new_ids,
    )


@router.get("/api/projects/{project_id}/molecules/{molecule_id}", response_model=MoleculeOut)
def get_molecule(
    molecule_id: str,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
) -> MoleculeOut:
    mol = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .filter(Molecule.id == molecule_id, Molecule.project_id == project.id)
        .first()
    )
    if mol is None or mol.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Molecule not found")
    return _mol_out(mol)


@router.delete("/api/projects/{project_id}/molecules/{molecule_id}", status_code=204)
def delete_molecule(
    molecule_id: str,
    confirm: bool = False,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
) -> None:
    if not confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Requires confirm=true")
    mol = (
        db.query(Molecule)
        .filter(Molecule.id == molecule_id, Molecule.project_id == project.id)
        .first()
    )
    if mol is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Molecule not found")
    mol.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


@router.post("/api/projects/{project_id}/molecules/{molecule_id}/restore", response_model=MoleculeOut)
def restore_molecule(
    molecule_id: str,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
) -> MoleculeOut:
    mol = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .filter(Molecule.id == molecule_id, Molecule.project_id == project.id)
        .first()
    )
    if mol is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Molecule not found")
    if mol.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Molecule is not deleted")
    days = get_settings().soft_delete_days
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    if mol.deleted_at < cutoff:
        raise HTTPException(status.HTTP_410_GONE, f"Restore window of {days} days has expired")
    mol.deleted_at = None
    db.commit()
    db.refresh(mol)
    return _mol_out(mol)
