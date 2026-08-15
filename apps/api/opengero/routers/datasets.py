from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import Dataset, User
from ..schemas import DatasetCompoundOut, DatasetOut

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetOut])
def list_datasets(_: User = Depends(current_user), db: Session = Depends(get_db)) -> list[DatasetOut]:
    return db.query(Dataset).order_by(Dataset.name).all()


@router.get("/{slug}", response_model=DatasetOut)
def get_dataset(slug: str, _: User = Depends(current_user), db: Session = Depends(get_db)) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.slug == slug).first()
    if ds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    return ds


@router.get("/{slug}/compounds", response_model=list[DatasetCompoundOut])
def list_compounds(
    slug: str, _: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[DatasetCompoundOut]:
    ds = db.query(Dataset).filter(Dataset.slug == slug).first()
    if ds is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    return ds.compounds
