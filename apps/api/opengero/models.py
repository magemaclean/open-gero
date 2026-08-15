from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), default="user")
    display_name: Mapped[str] = mapped_column(String(120), default="")

    projects: Mapped[list[Project]] = relationship(back_populates="owner")


class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")

    owner: Mapped[User] = relationship(back_populates="projects")
    molecules: Mapped[list[Molecule]] = relationship(back_populates="project")
    jobs: Mapped[list[Job]] = relationship(back_populates="project")
    saved_searches: Mapped[list[SavedSearch]] = relationship(back_populates="project")


class Molecule(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "molecules"
    __table_args__ = (UniqueConstraint("project_id", "inchikey", name="uq_project_inchikey"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), default="")
    smiles_raw: Mapped[str] = mapped_column(Text)
    canonical_smiles: Mapped[str] = mapped_column(Text, index=True)
    inchikey: Mapped[str] = mapped_column(String(27), index=True)
    formula: Mapped[str] = mapped_column(String(120), default="")
    source: Mapped[str] = mapped_column(String(80), default="manual")
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)

    project: Mapped[Project] = relationship(back_populates="molecules")
    properties: Mapped[MoleculeProperty | None] = relationship(
        back_populates="molecule", uselist=False
    )


class MoleculeProperty(Base):
    __tablename__ = "molecule_properties"

    molecule_id: Mapped[str] = mapped_column(ForeignKey("molecules.id"), primary_key=True)
    mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    logp: Mapped[float | None] = mapped_column(Float, nullable=True)
    tpsa: Mapped[float | None] = mapped_column(Float, nullable=True)
    hbd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hba: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rotatable_bonds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ring_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lipinski_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    veber_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    qed: Mapped[float | None] = mapped_column(Float, nullable=True)
    fp_morgan: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    molecule: Mapped[Molecule] = relationship(back_populates="properties")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(40))
    license: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(400), default="")
    compound_count: Mapped[int] = mapped_column(Integer, default=0)

    compounds: Mapped[list[DatasetCompound]] = relationship(back_populates="dataset")


class DatasetCompound(Base):
    __tablename__ = "dataset_compounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    smiles: Mapped[str] = mapped_column(Text)
    canonical_smiles: Mapped[str] = mapped_column(Text, default="")
    inchikey: Mapped[str] = mapped_column(String(27), default="", index=True)
    organism: Mapped[str] = mapped_column(String(120), default="")
    effect_size: Mapped[str] = mapped_column(String(80), default="")
    effect_note: Mapped[str] = mapped_column(Text, default="")
    citation: Mapped[str] = mapped_column(Text, default="")
    pmid: Mapped[str] = mapped_column(String(20), default="")
    fp_morgan: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="compounds")


class Target(Base, TimestampMixin):
    __tablename__ = "targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    uniprot: Mapped[str] = mapped_column(String(20), default="")
    pdb_id: Mapped[str] = mapped_column(String(8), default="")
    alphafold_id: Mapped[str] = mapped_column(String(40), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    pathway: Mapped[str] = mapped_column(String(120), default="")
    structure_kind: Mapped[str] = mapped_column(String(40), default="crystal")
    center_x: Mapped[float] = mapped_column(Float, default=0.0)
    center_y: Mapped[float] = mapped_column(Float, default=0.0)
    center_z: Mapped[float] = mapped_column(Float, default=0.0)
    size_x: Mapped[float] = mapped_column(Float, default=22.0)
    size_y: Mapped[float] = mapped_column(Float, default=22.0)
    size_z: Mapped[float] = mapped_column(Float, default=22.0)
    structure_uri: Mapped[str] = mapped_column(String(400), default="")
    version: Mapped[str] = mapped_column(String(20), default="1")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    params_hash: Mapped[str] = mapped_column(String(64), default="")
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped[Project] = relationship(back_populates="jobs")
    batches: Mapped[list[JobBatch]] = relationship(back_populates="job")
    docking_results: Mapped[list[DockingResult]] = relationship(back_populates="job")


class JobBatch(Base):
    __tablename__ = "job_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    molecule_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    job: Mapped[Job] = relationship(back_populates="batches")


class DockingResult(Base, TimestampMixin):
    __tablename__ = "docking_results"
    __table_args__ = (
        UniqueConstraint(
            "molecule_id", "target_id", "params_hash", name="uq_dock_cache"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    molecule_id: Mapped[str] = mapped_column(ForeignKey("molecules.id"), index=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("targets.id"), index=True)
    params_hash: Mapped[str] = mapped_column(String(64), index=True)
    best_score: Mapped[float] = mapped_column(Float)
    pose_uri: Mapped[str] = mapped_column(String(400), default="")
    engine: Mapped[str] = mapped_column(String(80), default="vina")
    cached: Mapped[bool] = mapped_column(Boolean, default=False)

    job: Mapped[Job] = relationship(back_populates="docking_results")
    molecule: Mapped[Molecule] = relationship()
    target: Mapped[Target] = relationship()


class SavedSearch(Base, TimestampMixin):
    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40))
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    project: Mapped[Project] = relationship(back_populates="saved_searches")


class ExportRecord(Base, TimestampMixin):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    format: Mapped[str] = mapped_column(String(16))
    filename: Mapped[str] = mapped_column(String(240), default="")
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
