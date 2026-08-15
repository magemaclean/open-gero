import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from .. import __version__
from ..chemistry import write_sdf
from ..db import get_db
from ..deps import current_user, owned_project
from ..docking import engine_name
from ..models import Dataset, DockingResult, ExportRecord, Job, Molecule, Project, User
from ..schemas import ExportIn, MethodsOut
from ..seed import dataset_version

router = APIRouter(tags=["exports"])


def _provenance(db: Session, project: Project, extra: dict | None = None) -> dict:
    payload = {
        "app": "OpenGero",
        "app_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": project.id,
        "project_name": project.name,
        "dataset_geroprotectors_version": dataset_version(db),
        "rdkit_version": _rdkit_version(),
        "docking_engine": engine_name(),
        "disclaimer": (
            "Research tool only. Outputs are computational predictions, not medical advice "
            "and not a substitute for experimental validation."
        ),
    }
    if extra:
        payload.update(extra)
    return payload


def _rdkit_version() -> str:
    try:
        from rdkit import rdBase

        return rdBase.rdkitVersion
    except Exception:
        return "unknown"


def _selected_mols(db: Session, project: Project, body: ExportIn) -> list[Molecule]:
    q = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .filter(Molecule.project_id == project.id, Molecule.deleted_at.is_(None))
    )
    if body.molecule_ids:
        q = q.filter(Molecule.id.in_(body.molecule_ids))
    return q.all()


@router.post("/api/projects/{project_id}/export")
def export_view(
    body: ExportIn,
    project: Project = Depends(owned_project),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    mols = _selected_mols(db, project, body)
    if not mols:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to export")
    docking_by_mol: dict[str, DockingResult] = {}
    extra: dict = {}
    if body.job_id:
        job = db.get(Job, body.job_id)
        if job:
            extra["job_id"] = job.id
            extra["job_type"] = job.type
            extra["job_params"] = job.params_json
            extra["params_hash"] = job.params_hash
            extra["seed"] = (job.params_json or {}).get("seed")
            rows = db.query(DockingResult).filter(DockingResult.job_id == job.id).all()
            docking_by_mol = {r.molecule_id: r for r in rows}
    provenance = _provenance(db, project, extra)
    rec = ExportRecord(
        project_id=project.id,
        user_id=user.id,
        format=body.format,
        filename=f"opengero-{project.name[:40]}.{body.format}",
        provenance_json=provenance,
    )
    db.add(rec)
    db.commit()

    if body.format == "csv":
        buf = io.StringIO()
        buf.write("# OpenGero provenance\n")
        for k, v in provenance.items():
            buf.write(f"# {k}: {v}\n")
        fieldnames = [
            "name",
            "canonical_smiles",
            "inchikey",
            "formula",
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
        ]
        if docking_by_mol:
            fieldnames += ["docking_score", "docking_engine", "cached"]
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for mol in mols:
            p = mol.properties
            row = {
                "name": mol.name,
                "canonical_smiles": mol.canonical_smiles,
                "inchikey": mol.inchikey,
                "formula": mol.formula,
                "mw": getattr(p, "mw", None),
                "logp": getattr(p, "logp", None),
                "tpsa": getattr(p, "tpsa", None),
                "hbd": getattr(p, "hbd", None),
                "hba": getattr(p, "hba", None),
                "rotatable_bonds": getattr(p, "rotatable_bonds", None),
                "ring_count": getattr(p, "ring_count", None),
                "lipinski_pass": getattr(p, "lipinski_pass", None),
                "veber_pass": getattr(p, "veber_pass", None),
                "qed": getattr(p, "qed", None),
            }
            dock = docking_by_mol.get(mol.id)
            if dock:
                row["docking_score"] = dock.best_score
                row["docking_engine"] = dock.engine
                row["cached"] = dock.cached
            writer.writerow(row)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{rec.filename}"'},
        )

    sdf_rows = []
    for mol in mols:
        p = mol.properties
        row = {
            "name": mol.name,
            "canonical_smiles": mol.canonical_smiles,
            "inchikey": mol.inchikey,
            "mw": getattr(p, "mw", ""),
            "logp": getattr(p, "logp", ""),
            "provenance_app_version": __version__,
        }
        dock = docking_by_mol.get(mol.id)
        if dock:
            row["docking_score"] = dock.best_score
            row["docking_engine"] = dock.engine
        sdf_rows.append(row)
    data = write_sdf(sdf_rows)
    return Response(
        content=data,
        media_type="chemical/x-mdl-sdfile",
        headers={"Content-Disposition": f'attachment; filename="{rec.filename}"'},
    )


@router.get("/api/projects/{project_id}/methods", response_model=MethodsOut)
def methods_paragraph(
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
) -> MethodsOut:
    ds = db.query(Dataset).filter(Dataset.slug == "geroprotectors").first()
    jobs = (
        db.query(Job)
        .filter(Job.project_id == project.id, Job.type == "docking", Job.status == "done")
        .order_by(Job.finished_at.desc())
        .all()
    )
    last = jobs[0] if jobs else None
    engine = engine_name()
    text = (
        f"In-silico screening was performed in OpenGero v{__version__}. "
        f"Structures were canonicalized with RDKit {_rdkit_version()} and identified by InChIKey. "
        "Drug-likeness descriptors (molecular weight, Crippen logP, TPSA, hydrogen-bond donors/acceptors, "
        "rotatable bonds, Lipinski and Veber flags) were computed with RDKit. "
        "Similarity searches used Morgan fingerprints (radius 2, 2048 bits) and the Tanimoto coefficient "
        f"against the bundled geroprotector reference set"
        f"{f' version {ds.version}' if ds else ''} "
        f"({ds.license if ds else 'see dataset manifest'}). "
    )
    if last:
        params = last.params_json or {}
        text += (
            f"Molecular docking used {engine} with exhaustiveness={params.get('exhaustiveness')}, "
            f"seed={params.get('seed')}, and a binding box of "
            f"{params.get('size_x')}×{params.get('size_y')}×{params.get('size_z')} Å "
            f"centered at ({params.get('center_x')}, {params.get('center_y')}, {params.get('center_z')}). "
            "Docking scores are prioritization heuristics, not experimental binding affinities. "
        )
    else:
        text += "No docking jobs have been completed in this project. "
    text += (
        "This software is a research tool; outputs are computational predictions and are not medical advice."
    )
    return MethodsOut(text=text, provenance=_provenance(db, project))
