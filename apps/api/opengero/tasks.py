"""Idempotent batch workers for descriptors and docking."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from .chemistry import compute_descriptors, fp_to_bytes, mol_from_smiles, morgan_fp
from .config import get_settings
from .db import SessionLocal
from .docking import dock_molecule
from .models import DockingResult, Job, JobBatch, Molecule, MoleculeProperty, Target
from .queue import publish_job_event
from .storage import write_bytes

log = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def process_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        if job.cancel_requested:
            job.status = "cancelled"
            job.finished_at = _utcnow()
            db.commit()
            publish_job_event(job_id, {"status": "cancelled"})
            return
        job.status = "running"
        job.started_at = job.started_at or _utcnow()
        db.commit()
        publish_job_event(job_id, _job_payload(job))
        batches = (
            db.query(JobBatch)
            .filter(JobBatch.job_id == job_id)
            .order_by(JobBatch.index)
            .all()
        )
        for batch in batches:
            db.refresh(job)
            if job.cancel_requested:
                job.status = "cancelled"
                job.finished_at = _utcnow()
                db.commit()
                publish_job_event(job_id, {"status": "cancelled"})
                return
            if batch.status == "done":
                continue
            _run_batch(db, job, batch)
            db.refresh(job)
            publish_job_event(job_id, _job_payload(job))
        db.refresh(job)
        if job.status != "cancelled":
            job.status = "failed" if job.failed_items and job.completed_items == 0 else "done"
            job.finished_at = _utcnow()
            db.commit()
            publish_job_event(job_id, _job_payload(job))
    except Exception as exc:
        log.exception("job %s crashed", job_id)
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = _utcnow()
            db.commit()
            publish_job_event(job_id, {"status": "failed", "error": str(exc)})
    finally:
        db.close()


def _run_batch(db: Session, job: Job, batch: JobBatch) -> None:
    batch.attempts += 1
    batch.status = "running"
    batch.started_at = _utcnow()
    db.commit()
    try:
        if job.type in {"descriptor_batch", "fingerprint_batch"}:
            _descriptors_batch(db, job, batch)
        elif job.type == "docking":
            _docking_batch(db, job, batch)
        else:
            raise ValueError(f"unknown job type {job.type}")
        batch.status = "done"
        batch.finished_at = _utcnow()
        db.commit()
    except Exception as exc:
        log.exception("batch %s failed", batch.id)
        batch.status = "failed"
        batch.error = str(exc)
        batch.finished_at = _utcnow()
        job.failed_items += len(batch.molecule_ids or [])
        db.commit()
        if batch.attempts < 3:
            batch.status = "queued"
            batch.error = f"retry {batch.attempts}: {exc}"
            db.commit()
            _run_batch(db, job, batch)


def _descriptors_batch(db: Session, job: Job, batch: JobBatch) -> None:
    for mid in batch.molecule_ids or []:
        mol = db.get(Molecule, mid)
        if mol is None or mol.deleted_at is not None:
            job.failed_items += 1
            continue
        rdkit_mol = mol_from_smiles(mol.canonical_smiles)
        if rdkit_mol is None:
            job.failed_items += 1
            continue
        desc = compute_descriptors(rdkit_mol)
        fp = fp_to_bytes(morgan_fp(rdkit_mol))
        props = db.get(MoleculeProperty, mid)
        if props is None:
            props = MoleculeProperty(molecule_id=mid)
            db.add(props)
        props.mw = desc.mw
        props.logp = desc.logp
        props.tpsa = desc.tpsa
        props.hbd = desc.hbd
        props.hba = desc.hba
        props.rotatable_bonds = desc.rotatable_bonds
        props.ring_count = desc.ring_count
        props.lipinski_pass = desc.lipinski_pass
        props.veber_pass = desc.veber_pass
        props.qed = desc.qed
        props.fp_morgan = fp
        mol.formula = desc.formula
        job.completed_items += 1
    db.commit()


def _docking_batch(db: Session, job: Job, batch: JobBatch) -> None:
    params = job.params_json or {}
    target = db.get(Target, params.get("target_id"))
    if target is None:
        raise ValueError("target not found")
    center = (
        float(params.get("center_x", target.center_x)),
        float(params.get("center_y", target.center_y)),
        float(params.get("center_z", target.center_z)),
    )
    size = (
        float(params.get("size_x", target.size_x)),
        float(params.get("size_y", target.size_y)),
        float(params.get("size_z", target.size_z)),
    )
    exhaustiveness = int(params.get("exhaustiveness", 8))
    seed = int(params.get("seed", 42))
    receptor = Path(target.structure_uri) if target.structure_uri else None
    for mid in batch.molecule_ids or []:
        mol = db.get(Molecule, mid)
        if mol is None or mol.deleted_at is not None:
            job.failed_items += 1
            continue
        existing = (
            db.query(DockingResult)
            .filter(
                DockingResult.molecule_id == mid,
                DockingResult.target_id == target.id,
                DockingResult.params_hash == job.params_hash,
            )
            .first()
        )
        if existing:
            job.completed_items += 1
            continue
        score, pose, engine = dock_molecule(
            mol.canonical_smiles,
            target.slug,
            center,
            size,
            exhaustiveness,
            seed,
            receptor,
        )
        pose_rel = f"poses/{job.id}/{mid}.pdbqt"
        write_bytes(pose_rel, pose.encode())
        db.add(
            DockingResult(
                job_id=job.id,
                molecule_id=mid,
                target_id=target.id,
                params_hash=job.params_hash,
                best_score=score,
                pose_uri=pose_rel,
                engine=engine,
                cached=False,
            )
        )
        job.completed_items += 1
    db.commit()


def _job_payload(job: Job) -> dict:
    batches = job.batches or []
    return {
        "id": job.id,
        "status": job.status,
        "completed_items": job.completed_items,
        "failed_items": job.failed_items,
        "total_items": job.total_items,
        "batches_done": sum(1 for b in batches if b.status == "done"),
        "batches_total": len(batches),
        "cached": job.cached,
        "error": job.error,
    }


def enqueue_or_run(job_id: str) -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        process_job(job_id)
        return
    from .queue import enqueue

    enqueue("opengero.tasks.process_job", job_id)
