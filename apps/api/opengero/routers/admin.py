from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import admin_user
from ..models import Job, Molecule, Project, User
from ..schemas import AdminStats, UserOut
from ..seed import dataset_version
from ..storage import disk_usage_bytes

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
def stats(_: User = Depends(admin_user), db: Session = Depends(get_db)) -> AdminStats:
    return AdminStats(
        users=db.query(User).filter(User.deleted_at.is_(None)).count(),
        projects=db.query(Project).filter(Project.deleted_at.is_(None)).count(),
        molecules=db.query(Molecule).filter(Molecule.deleted_at.is_(None)).count(),
        jobs_queued=db.query(Job).filter(Job.status == "queued").count(),
        jobs_running=db.query(Job).filter(Job.status == "running").count(),
        jobs_failed=db.query(Job).filter(Job.status == "failed").count(),
        disk_bytes=disk_usage_bytes(),
        dataset_version=dataset_version(db),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(admin_user), db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).filter(User.deleted_at.is_(None)).order_by(User.created_at).all()


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
    user.role = role
    db.commit()
    return {"id": user.id, "role": user.role}


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
