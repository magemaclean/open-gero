from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import admin_user
from ..docking import reported_engine, vina_available
from ..models import Job, Molecule, Project, User
from ..schemas import AdminStats, UserOut
from ..seed import dataset_version
from ..storage import disk_usage_bytes

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.deleted_at.is_(None)).count()


@router.get("/stats", response_model=AdminStats)
def stats(_: User = Depends(admin_user), db: Session = Depends(get_db)) -> AdminStats:
    engine = reported_engine()
    return AdminStats(
        users=db.query(User).filter(User.deleted_at.is_(None)).count(),
        projects=db.query(Project).filter(Project.deleted_at.is_(None)).count(),
        molecules=db.query(Molecule).filter(Molecule.deleted_at.is_(None)).count(),
        jobs_queued=db.query(Job).filter(Job.status == "queued").count(),
        jobs_running=db.query(Job).filter(Job.status == "running").count(),
        jobs_failed=db.query(Job).filter(Job.status == "failed").count(),
        disk_bytes=disk_usage_bytes(),
        dataset_version=dataset_version(db),
        docking_engine=engine,
        vina_available=engine == "autodock-vina" or vina_available(),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(
    include_disabled: bool = False,
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[User]:
    q = db.query(User)
    if not include_disabled:
        q = q.filter(User.deleted_at.is_(None))
    return q.order_by(User.created_at).all()


@router.post("/users/{user_id}/role")
def set_role(
    user_id: str,
    role: str,
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    if role not in {"admin", "user"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be admin or user")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.role == "admin" and role != "admin" and _admin_count(db) <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot demote the last admin")
    user.role = role
    db.commit()
    return {"id": user.id, "role": user.role}


@router.post("/users/{user_id}/disable")
def disable_user(
    user_id: str,
    actor: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot disable your own account")
    if user.role == "admin" and user.deleted_at is None and _admin_count(db) <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot disable the last admin")
    user.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"id": user.id, "disabled": True}


@router.post("/users/{user_id}/enable")
def enable_user(
    user_id: str,
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.deleted_at = None
    db.commit()
    return {"id": user.id, "disabled": False}


@router.get("/jobs")
def queue_health(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    return [
        {
            "id": j.id,
            "type": j.type,
            "status": j.status,
            "completed_items": j.completed_items,
            "total_items": j.total_items,
            "error": j.error,
            "created_at": j.created_at,
        }
        for j in jobs
    ]
