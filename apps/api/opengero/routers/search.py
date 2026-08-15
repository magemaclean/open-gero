from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..chemistry import (
    fp_to_bytes,
    mol_from_smiles,
    morgan_fp,
    substructure_match,
    tanimoto,
    tanimoto_bytes,
)
from ..db import get_db
from ..deps import owned_project
from ..models import Dataset, Molecule, Project, SavedSearch
from ..schemas import DatasetCompoundOut, SavedSearchIn, SimilarityIn, SubstructureIn
from .molecules import _mol_out

router = APIRouter(tags=["search"])


@router.post("/api/projects/{project_id}/search/similarity")
def similarity_search(
    body: SimilarityIn,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
):
    query_fp = None
    if body.molecule_id:
        mol = db.get(Molecule, body.molecule_id)
        if mol is None or mol.project_id != project.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Query molecule not found")
        if mol.properties and mol.properties.fp_morgan:
            from ..chemistry import fp_from_bytes

            query_fp = fp_from_bytes(mol.properties.fp_morgan)
        else:
            rd = mol_from_smiles(mol.canonical_smiles)
            query_fp = morgan_fp(rd) if rd else None
    elif body.smiles:
        rd = mol_from_smiles(body.smiles)
        if rd is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid query SMILES")
        query_fp = morgan_fp(rd)
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide smiles or molecule_id")
    if query_fp is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not fingerprint query")

    if body.against == "dataset":
        ds = db.query(Dataset).filter(Dataset.slug == body.dataset_slug).first()
        if ds is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
        hits: list[DatasetCompoundOut] = []
        for row in ds.compounds:
            if not row.fp_morgan:
                continue
            score = tanimoto_bytes(fp_to_bytes(query_fp), row.fp_morgan)
            if score >= body.threshold:
                hits.append(
                    DatasetCompoundOut(
                        id=row.id,
                        name=row.name,
                        smiles=row.smiles,
                        canonical_smiles=row.canonical_smiles,
                        inchikey=row.inchikey,
                        organism=row.organism,
                        effect_size=row.effect_size,
                        effect_note=row.effect_note,
                        citation=row.citation,
                        pmid=row.pmid,
                        tanimoto=round(score, 4),
                    )
                )
        hits.sort(key=lambda h: h.tanimoto or 0, reverse=True)
        return {
            "dataset": {"slug": ds.slug, "name": ds.name, "version": ds.version, "license": ds.license},
            "hits": hits[: body.limit],
        }

    results = []
    mols = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .filter(Molecule.project_id == project.id, Molecule.deleted_at.is_(None))
        .all()
    )
    for mol in mols:
        if not mol.properties or not mol.properties.fp_morgan:
            continue
        from ..chemistry import fp_from_bytes

        score = tanimoto(query_fp, fp_from_bytes(mol.properties.fp_morgan))
        if score >= body.threshold:
            item = _mol_out(mol).model_dump()
            item["tanimoto"] = round(score, 4)
            results.append(item)
    results.sort(key=lambda r: r["tanimoto"], reverse=True)
    return {"hits": results[: body.limit]}


@router.post("/api/projects/{project_id}/search/substructure")
def substructure_search(
    body: SubstructureIn,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
):
    from rdkit import Chem

    if Chem.MolFromSmarts(body.smarts) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid SMARTS")
    mols = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .filter(Molecule.project_id == project.id, Molecule.deleted_at.is_(None))
        .all()
    )
    hits = []
    for mol in mols:
        if substructure_match(body.smarts, mol.canonical_smiles):
            hits.append(_mol_out(mol))
        if len(hits) >= body.limit:
            break
    return {"hits": hits}


@router.get("/api/projects/{project_id}/searches")
def list_searches(project: Project = Depends(owned_project), db: Session = Depends(get_db)):
    rows = (
        db.query(SavedSearch)
        .filter(SavedSearch.project_id == project.id)
        .order_by(SavedSearch.created_at.desc())
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "kind": r.kind, "params": r.params_json, "created_at": r.created_at}
        for r in rows
    ]


@router.post("/api/projects/{project_id}/searches", status_code=201)
def save_search(
    body: SavedSearchIn,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
):
    row = SavedSearch(project_id=project.id, name=body.name, kind=body.kind, params_json=body.params)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "kind": row.kind, "params": row.params_json}
