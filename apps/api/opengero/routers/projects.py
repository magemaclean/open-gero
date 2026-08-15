from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..config import get_settings
from ..deps import current_user, owned_project, owned_project_any
from ..models import Job, Molecule, Project, User
from ..schemas import ProjectIn, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_out(db: Session, project: Project) -> ProjectOut:
    mols = (
        db.query(func.count(Molecule.id))
        .filter(Molecule.project_id == project.id, Molecule.deleted_at.is_(None))
        .scalar()
        or 0
    )
    jobs = db.query(func.count(Job.id)).filter(Job.project_id == project.id).scalar() or 0
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        molecule_count=mols,
        job_count=jobs,
        deleted_at=project.deleted_at,
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    deleted: bool = False,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    q = db.query(Project)
    if deleted:
        q = q.filter(Project.deleted_at.is_not(None))
    else:
        q = q.filter(Project.deleted_at.is_(None))
    if user.role != "admin":
        q = q.filter(Project.owner_id == user.id)
    return [_to_out(db, p) for p in q.order_by(Project.updated_at.desc()).all()]


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> ProjectOut:
    project = Project(owner_id=user.id, name=body.name, description=body.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_out(db, project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: Project = Depends(owned_project), db: Session = Depends(get_db)) -> ProjectOut:
    return _to_out(db, project)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    body: ProjectIn,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project.name = body.name
    project.description = body.description
    db.commit()
    db.refresh(project)
    return _to_out(db, project)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    confirm: bool = False,
    project: Project = Depends(owned_project),
    db: Session = Depends(get_db),
) -> None:
    if not confirm:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Destructive action requires confirm=true. Project will be soft-deleted for 30 days.",
        )
    project.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


@router.post("/{project_id}/restore", response_model=ProjectOut)
def restore_project(
    project: Project = Depends(owned_project_any),
    db: Session = Depends(get_db),
) -> ProjectOut:
    if project.deleted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Project is not deleted")
    days = get_settings().soft_delete_days
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    if project.deleted_at < cutoff:
        raise HTTPException(status.HTTP_410_GONE, f"Restore window of {days} days has expired")
    project.deleted_at = None
    db.commit()
    db.refresh(project)
    return _to_out(db, project)
