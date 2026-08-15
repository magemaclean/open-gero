from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session, joinedload

from ..chemistry import params_hash
from ..config import get_settings
from ..db import SessionLocal, get_db
from ..deps import current_user, owned_project
from ..models import DockingResult, Job, JobBatch, Molecule, Project, Target, User
from ..schemas import DockingResultOut, JobCreate, JobOut
from ..tasks import enqueue_or_run

router = APIRouter(tags=["jobs"])


def _job_out(job: Job) -> JobOut:
    batches = job.batches or []
    return JobOut(
        id=job.id,
        project_id=job.project_id,
        type=job.type,
        status=job.status,
        params_json=job.params_json or {},
        params_hash=job.params_hash,
        total_items=job.total_items,
        completed_items=job.completed_items,
        failed_items=job.failed_items,
        cached=job.cached,
        cancel_requested=job.cancel_requested,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        batches_done=sum(1 for b in batches if b.status == "done"),
        batches_total=len(batches),
    )


@router.get("/api/projects/{project_id}/jobs", response_model=list[JobOut])
def list_jobs(project: Project = Depends(owned_project), db: Session = Depends(get_db)) -> list[JobOut]:
    jobs = (
        db.query(Job)
        .options(joinedload(Job.batches))
        .filter(Job.project_id == project.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return [_job_out(j) for j in jobs]


@router.post("/api/projects/{project_id}/jobs", response_model=JobOut, status_code=201)
def create_job(
    body: JobCreate,
    project: Project = Depends(owned_project),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> JobOut:
    settings = get_settings()
    q = db.query(Molecule).filter(Molecule.project_id == project.id, Molecule.deleted_at.is_(None))
    if body.molecule_ids:
        q = q.filter(Molecule.id.in_(body.molecule_ids))
    mols = q.all()
    if not mols:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No molecules to process")
    if body.type == "docking":
        if len(mols) > settings.max_docking_library:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Docking limited to {settings.max_docking_library} molecules per job",
            )
        if not body.target_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "target_id required for docking")
        target = db.get(Target, body.target_id)
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")
        params = {
            "target_id": target.id,
            "target_version": target.version,
            "exhaustiveness": body.exhaustiveness,
            "seed": body.seed,
            "center_x": body.center_x if body.center_x is not None else target.center_x,
            "center_y": body.center_y if body.center_y is not None else target.center_y,
            "center_z": body.center_z if body.center_z is not None else target.center_z,
            "size_x": body.size_x if body.size_x is not None else target.size_x,
            "size_y": body.size_y if body.size_y is not None else target.size_y,
            "size_z": body.size_z if body.size_z is not None else target.size_z,
        }
    else:
        params = {"type": body.type}
    phash = params_hash(params)
    cached = False
    if body.type == "docking":
        cached_count = (
            db.query(DockingResult)
            .filter(
                DockingResult.target_id == params["target_id"],
                DockingResult.params_hash == phash,
                DockingResult.molecule_id.in_([m.id for m in mols]),
            )
            .count()
        )
        cached = cached_count == len(mols)
    job = Job(
        project_id=project.id,
        user_id=user.id,
        type=body.type,
        status="queued",
        params_json=params,
        params_hash=phash,
        total_items=len(mols),
        cached=cached,
    )
    db.add(job)
    db.flush()
    batch_size = body.batch_size or settings.default_batch_size
    ids = [m.id for m in mols]
    for i in range(0, len(ids), batch_size):
        db.add(JobBatch(job_id=job.id, index=i // batch_size, molecule_ids=ids[i : i + batch_size]))
    db.commit()
    db.refresh(job)
    job = db.query(Job).options(joinedload(Job.batches)).filter(Job.id == job.id).one()
    enqueue_or_run(job.id)
    job = db.query(Job).options(joinedload(Job.batches)).filter(Job.id == job.id).one()
    return _job_out(job)


@router.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> JobOut:
    job = db.query(Job).options(joinedload(Job.batches)).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    project = db.get(Project, job.project_id)
    if project and project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your job")
    return _job_out(job)


@router.post("/api/jobs/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> JobOut:
    job = db.query(Job).options(joinedload(Job.batches)).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    job.cancel_requested = True
    if job.status in {"queued"}:
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(job)
    return _job_out(job)


@router.get("/api/jobs/{job_id}/results", response_model=list[DockingResultOut])
def job_results(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    rows = (
        db.query(DockingResult)
        .options(joinedload(DockingResult.molecule))
        .filter(DockingResult.job_id == job_id)
        .all()
    )
    if not rows and job.type == "docking":
        mol_ids = []
        for batch in db.query(JobBatch).filter(JobBatch.job_id == job_id).all():
            mol_ids.extend(batch.molecule_ids or [])
        rows = (
            db.query(DockingResult)
            .options(joinedload(DockingResult.molecule))
            .filter(
                DockingResult.params_hash == job.params_hash,
                DockingResult.molecule_id.in_(mol_ids or [""]),
            )
            .all()
        )
    out = []
    for r in rows:
        out.append(
            DockingResultOut(
                id=r.id,
                job_id=job.id,
                molecule_id=r.molecule_id,
                molecule_name=r.molecule.name if r.molecule else "",
                canonical_smiles=r.molecule.canonical_smiles if r.molecule else "",
                target_id=r.target_id,
                best_score=r.best_score,
                pose_uri=r.pose_uri,
                engine=r.engine,
                cached=r.cached or job.cached,
                params_hash=r.params_hash,
            )
        )
    out.sort(key=lambda x: x.best_score)
    return out


@router.get("/api/jobs/{job_id}/poses/{molecule_id}")
def get_pose(
    job_id: str,
    molecule_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import PlainTextResponse

    from ..storage import read_bytes

    row = (
        db.query(DockingResult)
        .filter(DockingResult.job_id == job_id, DockingResult.molecule_id == molecule_id)
        .first()
    )
    if row is None:
        job = db.get(Job, job_id)
        if job:
            row = (
                db.query(DockingResult)
                .filter(
                    DockingResult.molecule_id == molecule_id,
                    DockingResult.params_hash == job.params_hash,
                )
                .first()
            )
    if row is None or not row.pose_uri:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pose not found")
    try:
        data = read_bytes(row.pose_uri)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pose file missing")
    return PlainTextResponse(data.decode("utf-8", errors="replace"), media_type="chemical/x-pdbqt")


@router.websocket("/api/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str, token: str | None = Query(default=None)):
    from ..auth import decode_token

    if not decode_token(token or ""):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        import asyncio
        import json

        from ..config import get_settings

        settings = get_settings()
        try:
            from redis.asyncio import Redis

            redis = Redis.from_url(settings.redis_url)
            pubsub = redis.pubsub()
            await pubsub.subscribe(f"job:{job_id}")
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("data"):
                    await websocket.send_text(msg["data"].decode() if isinstance(msg["data"], bytes) else msg["data"])
                else:
                    db = SessionLocal()
                    try:
                        job = db.query(Job).options(joinedload(Job.batches)).filter(Job.id == job_id).first()
                        if job:
                            await websocket.send_text(json.dumps(_job_out(job).model_dump(mode="json")))
                            if job.status in {"done", "failed", "cancelled"}:
                                break
                    finally:
                        db.close()
                    await asyncio.sleep(1.0)
        except Exception:
            import asyncio
            import json

            while True:
                db = SessionLocal()
                try:
                    job = db.query(Job).options(joinedload(Job.batches)).filter(Job.id == job_id).first()
                    if job:
                        await websocket.send_text(json.dumps(_job_out(job).model_dump(mode="json")))
                        if job.status in {"done", "failed", "cancelled"}:
                            break
                finally:
                    db.close()
                await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
