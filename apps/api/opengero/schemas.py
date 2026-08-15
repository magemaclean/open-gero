from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = ""


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    display_name: str
    created_at: datetime
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    molecule_count: int = 0
    job_count: int = 0
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class MoleculeIn(BaseModel):
    smiles: str
    name: str = ""


class PropertiesOut(BaseModel):
    mw: float | None = None
    logp: float | None = None
    tpsa: float | None = None
    hbd: int | None = None
    hba: int | None = None
    rotatable_bonds: int | None = None
    ring_count: int | None = None
    lipinski_pass: bool | None = None
    veber_pass: bool | None = None
    qed: float | None = None
    formula: str | None = None


class MoleculeOut(BaseModel):
    id: str
    project_id: str
    name: str
    smiles_raw: str
    canonical_smiles: str
    inchikey: str
    formula: str
    source: str
    source_row: int | None
    created_at: datetime
    deleted_at: datetime | None = None
    properties: PropertiesOut | None = None

    model_config = {"from_attributes": True}


class ImportReport(BaseModel):
    accepted: int
    rejected: int
    duplicates_merged: int
    errors: list[dict[str, Any]]
    molecule_ids: list[str]


class ColumnMap(BaseModel):
    smiles: str = "smiles"
    name: str | None = "name"


class FilterPredicate(BaseModel):
    field: str
    op: str
    value: float | int | bool | str


class SimilarityIn(BaseModel):
    smiles: str | None = None
    molecule_id: str | None = None
    threshold: float = 0.35
    against: str = "library"  # library | dataset
    dataset_slug: str = "geroprotectors"
    limit: int = 50


class SubstructureIn(BaseModel):
    smarts: str
    limit: int = 200


class SavedSearchIn(BaseModel):
    name: str
    kind: str
    params: dict[str, Any]


class JobCreate(BaseModel):
    type: str = Field(pattern="^(descriptor_batch|fingerprint_batch|docking)$")
    target_id: str | None = None
    molecule_ids: list[str] | None = None
    exhaustiveness: int = 8
    seed: int = 42
    center_x: float | None = None
    center_y: float | None = None
    center_z: float | None = None
    size_x: float | None = None
    size_y: float | None = None
    size_z: float | None = None
    batch_size: int | None = None


class JobOut(BaseModel):
    id: str
    project_id: str
    type: str
    status: str
    params_json: dict[str, Any]
    params_hash: str
    total_items: int
    completed_items: int
    failed_items: int
    cached: bool
    cancel_requested: bool
    error: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    batches_done: int = 0
    batches_total: int = 0

    model_config = {"from_attributes": True}


class DockingResultOut(BaseModel):
    id: str
    job_id: str
    molecule_id: str
    molecule_name: str = ""
    canonical_smiles: str = ""
    target_id: str
    best_score: float
    pose_uri: str
    engine: str
    cached: bool
    params_hash: str

    model_config = {"from_attributes": True}


class DatasetOut(BaseModel):
    id: str
    slug: str
    name: str
    version: str
    license: str
    description: str
    source_url: str
    compound_count: int

    model_config = {"from_attributes": True}


class DatasetCompoundOut(BaseModel):
    id: str
    name: str
    smiles: str
    canonical_smiles: str
    inchikey: str
    organism: str
    effect_size: str
    effect_note: str
    citation: str
    pmid: str
    tanimoto: float | None = None

    model_config = {"from_attributes": True}


class TargetIn(BaseModel):
    pdb_id: str | None = None
    slug: str | None = None
    name: str | None = None
    uniprot: str = ""
    alphafold_id: str = ""
    description: str = ""
    pathway: str = ""
    structure_kind: str = "crystal"
    center_x: float = 0.0
    center_y: float = 0.0
    center_z: float = 0.0
    size_x: float = 22.0
    size_y: float = 22.0
    size_z: float = 22.0


class TargetOut(BaseModel):
    id: str
    slug: str
    name: str
    uniprot: str
    pdb_id: str
    alphafold_id: str
    description: str
    pathway: str
    structure_kind: str
    center_x: float
    center_y: float
    center_z: float
    size_x: float
    size_y: float
    size_z: float
    structure_uri: str
    version: str

    model_config = {"from_attributes": True}


class ExportIn(BaseModel):
    format: str = Field(pattern="^(csv|sdf)$")
    molecule_ids: list[str] | None = None
    job_id: str | None = None
    include_docking: bool = False


class MethodsOut(BaseModel):
    text: str
    provenance: dict[str, Any]


class AdminStats(BaseModel):
    users: int
    projects: int
    molecules: int
    jobs_queued: int
    jobs_running: int
    jobs_failed: int
    disk_bytes: int
    dataset_version: str
    docking_engine: str
    vina_available: bool
