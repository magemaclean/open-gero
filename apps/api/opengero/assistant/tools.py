from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from ..chemistry import parse_smiles_table
from ..config import get_settings
from ..models import Dataset, Molecule, MoleculeProperty, Project, Target, User
from ..schemas import ExportIn, JobCreate, MoleculeIn, ProjectIn, SavedSearchIn
from .pending import put_download

WRITE_TOOLS = {
    "create_project",
    "update_project",
    "import_smiles",
    "add_molecule",
    "save_search",
    "queue_docking",
    "cancel_job",
    "export_library",
}

_SCHEMA_EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}

TOOLS: list[dict[str, Any]] = [
    {"name": "get_meta", "description": "App version, docking engine, and research disclaimer.", "input_schema": _SCHEMA_EMPTY},
    {
        "name": "explain_metrics",
        "description": "Explain QED, Lipinski, Veber, Tanimoto, and heuristic-v0 vs AutoDock Vina.",
        "input_schema": _SCHEMA_EMPTY,
    },
    {"name": "list_projects", "description": "List the signed-in user's projects.", "input_schema": _SCHEMA_EMPTY},
    {
        "name": "get_project",
        "description": "Get one project by id.",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "list_molecules",
        "description": "List library molecules with optional filters. Compact rows; default 20.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "q": {"type": "string"},
                "lipinski": {"type": "boolean"},
                "veber": {"type": "boolean"},
                "mw_min": {"type": "number"},
                "mw_max": {"type": "number"},
                "tpsa_max": {"type": "number"},
                "logp_max": {"type": "number"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "get_molecule",
        "description": "Get one molecule dossier (structure, properties).",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}, "molecule_id": {"type": "string"}},
            "required": ["project_id", "molecule_id"],
        },
    },
    {
        "name": "list_jobs",
        "description": "List docking and descriptor jobs for a project.",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "get_job",
        "description": "Job status and progress.",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    },
    {
        "name": "get_job_results",
        "description": "Ranked docking scores for a finished job (top 25).",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    },
    {
        "name": "get_methods",
        "description": "Auto-written methods paragraph and provenance for a project.",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {"name": "list_targets", "description": "Aging target catalog (PDB / AlphaFold).", "input_schema": _SCHEMA_EMPTY},
    {"name": "list_datasets", "description": "Bundled geroprotector dataset metadata.", "input_schema": _SCHEMA_EMPTY},
    {
        "name": "search_similarity",
        "description": "Morgan/Tanimoto similarity vs the project library or geroprotector dataset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "smiles": {"type": "string"},
                "molecule_id": {"type": "string"},
                "against": {"type": "string", "enum": ["library", "dataset"]},
                "threshold": {"type": "number"},
                "limit": {"type": "integer"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "search_substructure",
        "description": "SMARTS substructure search over the project library.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "smarts": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["project_id", "smarts"],
        },
    },
    {
        "name": "list_saved_searches",
        "description": "Saved similarity/substructure queries for a project.",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "create_project",
        "description": "Create a project. Requires user confirm in the UI before it runs.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "update_project",
        "description": "Rename or edit a project description. Requires confirm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["project_id", "name"],
        },
    },
    {
        "name": "import_smiles",
        "description": "Import a SMILES table (one smiles[ name] per line). Requires confirm.",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["project_id", "text"],
        },
    },
    {
        "name": "add_molecule",
        "description": "Add one SMILES to the library. Requires confirm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "smiles": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["project_id", "smiles"],
        },
    },
    {
        "name": "save_search",
        "description": "Save a search query. Requires confirm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "name": {"type": "string"},
                "kind": {"type": "string"},
                "params": {"type": "object"},
            },
            "required": ["project_id", "name", "kind"],
        },
    },
    {
        "name": "queue_docking",
        "description": "Queue a docking job vs a catalog target. Requires confirm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "target_id": {"type": "string"},
                "target_slug": {"type": "string"},
                "molecule_ids": {"type": "array", "items": {"type": "string"}},
                "exhaustiveness": {"type": "integer"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "cancel_job",
        "description": "Request cancel on a queued/running job. Requires confirm.",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    },
    {
        "name": "export_library",
        "description": "Build a CSV or SDF export. Requires confirm; returns a short-lived download URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "format": {"type": "string", "enum": ["csv", "sdf"]},
                "molecule_ids": {"type": "array", "items": {"type": "string"}},
                "job_id": {"type": "string"},
            },
            "required": ["project_id"],
        },
    },
]

TOOL_INDEX = {t["name"]: t for t in TOOLS}


def summarize(name: str, args: dict[str, Any]) -> str:
    if name == "create_project":
        return f"Create project “{args.get('name', '')}”"
    if name == "update_project":
        return f"Update project {args.get('project_id', '')} to “{args.get('name', '')}”"
    if name == "import_smiles":
        lines = [ln for ln in str(args.get("text") or "").splitlines() if ln.strip() and not ln.strip().startswith("#")]
        return f"Import {len(lines)} SMILES into project {args.get('project_id', '')}"
    if name == "add_molecule":
        return f"Add {args.get('name') or args.get('smiles')} to project {args.get('project_id', '')}"
    if name == "save_search":
        return f"Save search “{args.get('name', '')}”"
    if name == "queue_docking":
        target = args.get("target_slug") or args.get("target_id") or "catalog target"
        n = len(args.get("molecule_ids") or []) or "library"
        return f"Queue docking of {n} molecule(s) vs {target}"
    if name == "cancel_job":
        return f"Cancel job {args.get('job_id', '')}"
    if name == "export_library":
        return f"Export {args.get('format') or 'csv'} from project {args.get('project_id', '')}"
    return name.replace("_", " ")


def _owned_project(db: Session, user: User, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(404, "Project not found")
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(403, "Not your project")
    return project


def _compact_mol(mol: Molecule) -> dict[str, Any]:
    p = mol.properties
    return {
        "id": mol.id,
        "name": mol.name,
        "smiles": mol.canonical_smiles,
        "inchikey": mol.inchikey,
        "mw": getattr(p, "mw", None),
        "logp": getattr(p, "logp", None),
        "tpsa": getattr(p, "tpsa", None),
        "qed": getattr(p, "qed", None),
        "lipinski_pass": getattr(p, "lipinski_pass", None),
        "veber_pass": getattr(p, "veber_pass", None),
    }


def _dump(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model


def run_tool(
    name: str,
    args: dict[str, Any],
    *,
    db: Session,
    user: User,
    allow_writes: bool,
    default_project_id: str | None = None,
) -> dict[str, Any]:
    if name not in TOOL_INDEX:
        return {"error": f"Unknown tool {name}"}
    args = dict(args or {})
    if not args.get("project_id") and default_project_id and "project_id" in TOOL_INDEX[name].get("input_schema", {}).get("properties", {}):
        args["project_id"] = default_project_id
    if name in WRITE_TOOLS and not allow_writes:
        return {"_pending": True, "name": name, "arguments": args, "summary": summarize(name, args)}
    try:
        handler = _HANDLERS[name]
        result = handler(db, user, args)
        return {"ok": True, "result": result}
    except HTTPException as exc:
        return {"error": exc.detail if isinstance(exc.detail, str) else str(exc.detail), "status": exc.status_code}
    except Exception as exc:
        return {"error": str(exc)}


def _get_meta(_db: Session, _user: User, _args: dict[str, Any]) -> dict[str, Any]:
    from .. import __version__
    from ..docking import reported_engine, vina_available

    engine = reported_engine()
    return {
        "name": "OpenGero",
        "version": __version__,
        "docking_engine": engine,
        "vina_available": engine == "autodock-vina" or vina_available(),
        "disclaimer": "Research tool only. Not medical advice. Scores are prioritization heuristics.",
    }


def _explain(_db: Session, _user: User, _args: dict[str, Any]) -> dict[str, Any]:
    return {
        "qed": "Quantitative Estimate of Drug-likeness (0–1). Missing values show as — , not 0.00.",
        "lipinski": "Rule of five: MW ≤500, logP ≤5, HBD ≤5, HBA ≤10.",
        "veber": "Oral bioavailability heuristic: rotatable bonds ≤10 and TPSA ≤140.",
        "tanimoto": "Morgan fingerprint similarity (radius 2, 2048 bits) vs library or geroprotectors.",
        "heuristic-v0": "Used when AutoDock Vina is not on the worker. Not a binding energy.",
        "vina": "AutoDock Vina score when vina + Open Babel are available. Still a computational heuristic.",
    }


def _list_projects(db: Session, user: User, _args: dict[str, Any]) -> list[dict[str, Any]]:
    from ..routers.projects import list_projects

    return [_dump(p) for p in list_projects(deleted=False, user=user, db=db)]


def _get_project(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.projects import _to_out

    return _dump(_to_out(db, _owned_project(db, user, args["project_id"])))


def _list_molecules(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    project = _owned_project(db, user, args["project_id"])
    query = (
        db.query(Molecule)
        .options(joinedload(Molecule.properties))
        .outerjoin(MoleculeProperty, MoleculeProperty.molecule_id == Molecule.id)
        .filter(Molecule.project_id == project.id, Molecule.deleted_at.is_(None))
    )
    q = args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Molecule.name.ilike(like)) | (Molecule.canonical_smiles.ilike(like)) | (Molecule.inchikey.ilike(like))
        )
    if args.get("lipinski") is not None:
        query = query.filter(MoleculeProperty.lipinski_pass.is_(bool(args["lipinski"])))
    if args.get("veber") is not None:
        query = query.filter(MoleculeProperty.veber_pass.is_(bool(args["veber"])))
    if args.get("mw_max") is not None:
        query = query.filter(MoleculeProperty.mw.is_not(None), MoleculeProperty.mw <= float(args["mw_max"]))
    if args.get("mw_min") is not None:
        query = query.filter(MoleculeProperty.mw.is_not(None), MoleculeProperty.mw >= float(args["mw_min"]))
    if args.get("tpsa_max") is not None:
        query = query.filter(MoleculeProperty.tpsa.is_not(None), MoleculeProperty.tpsa <= float(args["tpsa_max"]))
    if args.get("logp_max") is not None:
        query = query.filter(MoleculeProperty.logp.is_not(None), MoleculeProperty.logp <= float(args["logp_max"]))
    total = query.count()
    limit = min(int(args.get("limit") or 20), 50)
    offset = int(args.get("offset") or 0)
    rows = query.order_by(Molecule.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "items": [_compact_mol(m) for m in rows]}


def _get_molecule(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.molecules import _mol_out

    project = _owned_project(db, user, args["project_id"])
    mol = db.get(Molecule, args["molecule_id"])
    if mol is None or mol.project_id != project.id:
        raise HTTPException(404, "Molecule not found")
    return _dump(_mol_out(mol))


def _list_jobs(db: Session, user: User, args: dict[str, Any]) -> list[dict[str, Any]]:
    from ..routers.jobs import list_jobs

    return [_dump(j) for j in list_jobs(_owned_project(db, user, args["project_id"]), db)]


def _get_job(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.jobs import get_job

    return _dump(get_job(args["job_id"], user, db))


def _job_results(db: Session, user: User, args: dict[str, Any]) -> list[dict[str, Any]]:
    from ..routers.jobs import job_results

    rows = job_results(args["job_id"], user, db)
    return [_dump(r) for r in rows[:25]]


def _methods(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.exports import methods_paragraph

    return _dump(methods_paragraph(_owned_project(db, user, args["project_id"]), db))


def _targets(db: Session, _user: User, _args: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.query(Target).order_by(Target.name).all()
    return [
        {
            "id": t.id,
            "slug": t.slug,
            "name": t.name,
            "pdb_id": t.pdb_id,
            "structure_kind": t.structure_kind,
            "pathway": t.pathway,
        }
        for t in rows
    ]


def _datasets(db: Session, _user: User, _args: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.query(Dataset).order_by(Dataset.name).all()
    return [{"slug": d.slug, "name": d.name, "version": d.version, "license": d.license, "compound_count": d.compound_count} for d in rows]


def _similarity(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.search import similarity_search
    from ..schemas import SimilarityIn

    body = SimilarityIn(
        smiles=args.get("smiles"),
        molecule_id=args.get("molecule_id"),
        against=args.get("against") or "dataset",
        threshold=float(args.get("threshold") or 0.35),
        limit=min(int(args.get("limit") or 10), 25),
    )
    result = similarity_search(body, _owned_project(db, user, args["project_id"]), db)
    hits = result.get("hits") or []
    compact = []
    for hit in hits[:15]:
        if hasattr(hit, "model_dump"):
            row = hit.model_dump(mode="json")
            compact.append({k: row.get(k) for k in ("id", "name", "smiles", "organism", "effect_note", "pmid", "tanimoto", "canonical_smiles") if k in row})
        elif isinstance(hit, dict):
            compact.append(hit)
        else:
            compact.append(_dump(hit))
    out = {"hits": compact}
    if "dataset" in result:
        out["dataset"] = result["dataset"]
    return out


def _substructure(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.search import substructure_search
    from ..schemas import SubstructureIn

    body = SubstructureIn(smarts=args["smarts"], limit=min(int(args.get("limit") or 25), 50))
    result = substructure_search(body, _owned_project(db, user, args["project_id"]), db)
    hits = result.get("hits") or []
    return {"hits": [_compact_mol(h) if isinstance(h, Molecule) else _dump(h) for h in hits[:20]]}


def _list_searches(db: Session, user: User, args: dict[str, Any]) -> list[dict[str, Any]]:
    from ..routers.search import list_searches

    return list_searches(_owned_project(db, user, args["project_id"]), db)


def _create_project(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.projects import create_project

    return _dump(create_project(ProjectIn(name=str(args["name"]), description=str(args.get("description") or "")), user, db))


def _update_project(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.projects import update_project

    project = _owned_project(db, user, args["project_id"])
    return _dump(update_project(ProjectIn(name=str(args["name"]), description=str(args.get("description") or project.description)), project, db))


def _import_smiles(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.molecules import _apply_properties, _upsert
    from ..chemistry import params_hash
    from ..models import Job, JobBatch
    from ..tasks import enqueue_or_run

    project = _owned_project(db, user, args["project_id"])
    settings = get_settings()
    parsed_rows = parse_smiles_table(str(args.get("text") or ""))
    if len(parsed_rows) > settings.max_import_rows:
        raise HTTPException(400, f"Import exceeds {settings.max_import_rows} row limit")
    accepted = 0
    rejected = 0
    duplicates = 0
    errors: list[dict[str, Any]] = []
    new_ids: list[str] = []
    for parsed in parsed_rows:
        if parsed.error:
            rejected += 1
            errors.append({"row": parsed.source_row, "name": parsed.name, "error": parsed.error})
            continue
        mol, kind = _upsert(db, project.id, parsed, "smiles")
        if kind == "duplicate":
            duplicates += 1
        elif kind == "new" and mol:
            accepted += 1
            new_ids.append(mol.id)
        else:
            rejected += 1
    db.commit()
    if new_ids and len(new_ids) <= settings.descriptor_inline_limit:
        for mid in new_ids:
            mol = db.get(Molecule, mid)
            if mol:
                _apply_properties(db, mol)
        db.commit()
    elif new_ids:
        job = Job(
            project_id=project.id,
            user_id=user.id,
            type="descriptor_batch",
            status="queued",
            params_json={"source": "assistant"},
            params_hash=params_hash({"type": "descriptor_batch", "n": len(new_ids)}),
            total_items=len(new_ids),
        )
        db.add(job)
        db.flush()
        batch_size = settings.default_batch_size
        for i in range(0, len(new_ids), batch_size):
            db.add(JobBatch(job_id=job.id, index=i // batch_size, molecule_ids=new_ids[i : i + batch_size]))
        db.commit()
        enqueue_or_run(job.id)
    return {"accepted": accepted, "rejected": rejected, "duplicates_merged": duplicates, "errors": errors[:50], "molecule_ids": new_ids[:50]}


def _add_molecule(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.molecules import add_molecule

    return _dump(add_molecule(MoleculeIn(smiles=str(args["smiles"]), name=str(args.get("name") or "")), _owned_project(db, user, args["project_id"]), db))


def _save_search(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.search import save_search

    body = SavedSearchIn(name=str(args["name"]), kind=str(args["kind"]), params=args.get("params") or {})
    return save_search(body, _owned_project(db, user, args["project_id"]), db)


def _queue_docking(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.jobs import create_job

    project = _owned_project(db, user, args["project_id"])
    target_id = args.get("target_id")
    slug = args.get("target_slug")
    if not target_id and slug:
        target = db.query(Target).filter(Target.slug == slug).first()
        if target is None:
            raise HTTPException(404, "Target not found")
        target_id = target.id
    body = JobCreate(
        type="docking",
        target_id=target_id,
        molecule_ids=args.get("molecule_ids"),
        exhaustiveness=int(args.get("exhaustiveness") or 8),
    )
    return _dump(create_job(body, project, user, db))


def _cancel_job(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.jobs import cancel_job

    return _dump(cancel_job(args["job_id"], user, db))


def _export_library(db: Session, user: User, args: dict[str, Any]) -> dict[str, Any]:
    from ..routers.exports import export_view

    fmt = args.get("format") or "csv"
    project = _owned_project(db, user, args["project_id"])
    body = ExportIn(
        format=fmt,
        molecule_ids=args.get("molecule_ids"),
        job_id=args.get("job_id"),
        include_docking=bool(args.get("job_id")),
    )
    resp = export_view(body, project, user, db)
    content = resp.body if isinstance(resp.body, (bytes, bytearray)) else bytes(resp.body)
    filename = f"{project.name.replace(' ', '_')}.{fmt}"
    download_id = put_download(user.id, filename, bytes(content), resp.media_type or "application/octet-stream")
    return {"filename": filename, "url": f"/api/assistant/downloads/{download_id}", "bytes": len(content)}


_HANDLERS: dict[str, Callable[[Session, User, dict[str, Any]], Any]] = {
    "get_meta": _get_meta,
    "explain_metrics": _explain,
    "list_projects": _list_projects,
    "get_project": _get_project,
    "list_molecules": _list_molecules,
    "get_molecule": _get_molecule,
    "list_jobs": _list_jobs,
    "get_job": _get_job,
    "get_job_results": _job_results,
    "get_methods": _methods,
    "list_targets": _targets,
    "list_datasets": _datasets,
    "search_similarity": _similarity,
    "search_substructure": _substructure,
    "list_saved_searches": _list_searches,
    "create_project": _create_project,
    "update_project": _update_project,
    "import_smiles": _import_smiles,
    "add_molecule": _add_molecule,
    "save_search": _save_search,
    "queue_docking": _queue_docking,
    "cancel_job": _cancel_job,
    "export_library": _export_library,
}
