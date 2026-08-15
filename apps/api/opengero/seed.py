from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from .auth import hash_password
from .chemistry import compute_descriptors, fp_to_bytes, mol_from_smiles, morgan_fp, parse_smiles
from .config import get_settings
from .models import (
    Dataset,
    DatasetCompound,
    Molecule,
    MoleculeProperty,
    Project,
    Target,
    User,
)

log = logging.getLogger(__name__)

DEMO_EMAIL = "demo@opengero.local"
DEMO_PASSWORD = "demo12345"


def seed_all(db: Session) -> None:
    _seed_admin(db)
    _seed_datasets(db)
    _seed_targets(db)
    _seed_demo_project(db)
    db.commit()


def _seed_admin(db: Session) -> User:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user:
        return user
    user = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        role="admin",
        display_name="Demo Researcher",
    )
    db.add(user)
    db.flush()
    return user


def _seed_datasets(db: Session) -> None:
    settings = get_settings()
    manifest_path = settings.datasets_dir / "manifest.json"
    if not manifest_path.exists():
        log.warning("dataset manifest missing at %s", manifest_path)
        return
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest.get("datasets", []):
        existing = db.query(Dataset).filter(Dataset.slug == entry["slug"]).first()
        if existing:
            continue
        data_path = settings.datasets_dir / entry["file"]
        compounds = json.loads(data_path.read_text())
        ds = Dataset(
            slug=entry["slug"],
            name=entry["name"],
            version=entry["version"],
            license=entry["license"],
            description=entry.get("description", ""),
            source_url=entry.get("source_url", ""),
            compound_count=len(compounds),
        )
        db.add(ds)
        db.flush()
        for row in compounds:
            parsed = parse_smiles(row["smiles"], name=row["name"])
            fp = None
            if parsed.canonical_smiles:
                mol = mol_from_smiles(parsed.canonical_smiles)
                if mol is not None:
                    fp = fp_to_bytes(morgan_fp(mol))
            db.add(
                DatasetCompound(
                    dataset_id=ds.id,
                    name=row["name"],
                    smiles=row["smiles"],
                    canonical_smiles=parsed.canonical_smiles,
                    inchikey=parsed.inchikey,
                    organism=row.get("organism", ""),
                    effect_size=row.get("effect_size", ""),
                    effect_note=row.get("effect_note", ""),
                    citation=row.get("citation", ""),
                    pmid=row.get("pmid", ""),
                    fp_morgan=fp,
                )
            )


def _seed_targets(db: Session) -> None:
    settings = get_settings()
    catalog = settings.targets_dir / "catalog.json"
    if not catalog.exists():
        return
    rows = json.loads(catalog.read_text())
    for row in rows:
        if db.query(Target).filter(Target.slug == row["slug"]).first():
            continue
        db.add(Target(**row))


def _seed_demo_project(db: Session) -> None:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user is None:
        return
    existing = (
        db.query(Project)
        .filter(Project.owner_id == user.id, Project.name == "Senolytic shortlist")
        .first()
    )
    if existing:
        return
    project = Project(
        owner_id=user.id,
        name="Senolytic shortlist",
        description="Demo library of candidate geroprotectors and senolytics for the OpenGero walkthrough.",
    )
    db.add(project)
    db.flush()
    demo_path = get_settings().datasets_dir / "demo_library.json"
    if not demo_path.exists():
        return
    for i, row in enumerate(json.loads(demo_path.read_text()), start=1):
        parsed = parse_smiles(row["smiles"], name=row["name"], source_row=i)
        if parsed.error:
            continue
        mol = Molecule(
            project_id=project.id,
            name=parsed.name,
            smiles_raw=parsed.smiles_raw,
            canonical_smiles=parsed.canonical_smiles,
            inchikey=parsed.inchikey,
            source="seed",
            source_row=i,
        )
        db.add(mol)
        db.flush()
        rdkit_mol = mol_from_smiles(parsed.canonical_smiles)
        if rdkit_mol is None:
            continue
        desc = compute_descriptors(rdkit_mol)
        mol.formula = desc.formula
        db.add(
            MoleculeProperty(
                molecule_id=mol.id,
                mw=desc.mw,
                logp=desc.logp,
                tpsa=desc.tpsa,
                hbd=desc.hbd,
                hba=desc.hba,
                rotatable_bonds=desc.rotatable_bonds,
                ring_count=desc.ring_count,
                lipinski_pass=desc.lipinski_pass,
                veber_pass=desc.veber_pass,
                qed=desc.qed,
                fp_morgan=fp_to_bytes(morgan_fp(rdkit_mol)),
            )
        )


def dataset_version(db: Session) -> str:
    ds = db.query(Dataset).filter(Dataset.slug == "geroprotectors").first()
    return ds.version if ds else "unseeded"
