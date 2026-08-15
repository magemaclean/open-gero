import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import admin_user, current_user
from ..models import Target, User
from ..schemas import TargetIn, TargetOut

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get("", response_model=list[TargetOut])
def list_targets(_: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Target]:
    return db.query(Target).order_by(Target.name).all()


@router.get("/{target_id}", response_model=TargetOut)
def get_target(target_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)) -> Target:
    target = db.get(Target, target_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")
    return target


@router.post("", response_model=TargetOut, status_code=201)
def create_target(
    body: TargetIn,
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> Target:
    pdb_id = (body.pdb_id or "").upper().strip()
    slug = body.slug or (pdb_id.lower() if pdb_id else None)
    if not slug:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "slug or pdb_id required")
    if db.query(Target).filter(Target.slug == slug).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Target slug exists")
    name = body.name or pdb_id or slug
    description = body.description
    if pdb_id and re.fullmatch(r"[0-9][A-Z0-9]{3}", pdb_id):
        try:
            resp = httpx.get(
                f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}",
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                name = body.name or data.get("struct", {}).get("title") or name
                description = description or data.get("struct", {}).get("title") or ""
        except httpx.HTTPError:
            pass
    target = Target(
        slug=slug,
        name=name,
        uniprot=body.uniprot,
        pdb_id=pdb_id,
        alphafold_id=body.alphafold_id,
        description=description,
        pathway=body.pathway,
        structure_kind=body.structure_kind if not body.alphafold_id else "alphafold",
        center_x=body.center_x,
        center_y=body.center_y,
        center_z=body.center_z,
        size_x=body.size_x,
        size_y=body.size_y,
        size_z=body.size_z,
        structure_uri=f"https://files.rcsb.org/download/{pdb_id}.pdb" if pdb_id else "",
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target
