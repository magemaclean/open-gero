"""Docking engines: AutoDock Vina when present, deterministic heuristic otherwise."""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from .chemistry import descriptors_from_smiles, smiles_to_pdb_block
from .config import get_settings

log = logging.getLogger(__name__)


def vina_available() -> bool:
    settings = get_settings()
    return shutil.which(settings.vina_binary) is not None


def engine_name() -> str:
    if vina_available():
        return "autodock-vina"
    return "heuristic-v0"


def heuristic_score(smiles: str, target_slug: str, seed: int) -> float:
    """Deterministic prioritization heuristic — not a binding free energy.

    Used when Vina is not installed so the workbench remains usable.
    Scores are labeled as heuristics in the UI and exports.
    """
    desc = descriptors_from_smiles(smiles) or {}
    mw = float(desc.get("mw") or 350)
    logp = float(desc.get("logp") or 2)
    tpsa = float(desc.get("tpsa") or 80)
    qed = float(desc.get("qed") or 0.5)
    lip = 1.0 if desc.get("lipinski_pass") else 0.0
    digest = hashlib.sha256(f"{smiles}|{target_slug}|{seed}".encode()).digest()
    noise = int.from_bytes(digest[:2], "big") / 65535.0 - 0.5
    mw_pen = abs(mw - 380) / 120.0
    logp_pen = abs(logp - 2.8) / 3.0
    tpsa_pen = max(0.0, tpsa - 140) / 80.0
    score = -4.2 - 2.8 * qed - 0.8 * lip + 0.9 * mw_pen + 0.5 * logp_pen + tpsa_pen + noise
    return round(score, 3)


def run_vina(
    ligand_pdb: str,
    receptor_path: Path | None,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    exhaustiveness: int,
    seed: int,
) -> tuple[float, str] | None:
    settings = get_settings()
    if not vina_available():
        return None
    obabel = shutil.which(settings.obabel_binary)
    if obabel is None or receptor_path is None or not receptor_path.exists():
        return None
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        lig_pdb = tmp_path / "lig.pdb"
        lig_pdbqt = tmp_path / "lig.pdbqt"
        rec_pdbqt = tmp_path / "rec.pdbqt"
        out_pdbqt = tmp_path / "out.pdbqt"
        lig_pdb.write_text(ligand_pdb)
        subprocess.run(
            [obabel, str(lig_pdb), "-O", str(lig_pdbqt)],
            check=True,
            capture_output=True,
            timeout=60,
        )
        subprocess.run(
            [obabel, str(receptor_path), "-O", str(rec_pdbqt)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        cmd = [
            settings.vina_binary,
            "--receptor",
            str(rec_pdbqt),
            "--ligand",
            str(lig_pdbqt),
            "--center_x",
            str(center[0]),
            "--center_y",
            str(center[1]),
            "--center_z",
            str(center[2]),
            "--size_x",
            str(size[0]),
            "--size_y",
            str(size[1]),
            "--size_z",
            str(size[2]),
            "--exhaustiveness",
            str(exhaustiveness),
            "--seed",
            str(seed),
            "--out",
            str(out_pdbqt),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0 or not out_pdbqt.exists():
            log.warning("vina failed: %s", proc.stderr)
            return None
        score = _parse_vina_score(out_pdbqt.read_text() + "\n" + proc.stdout)
        return score, out_pdbqt.read_text()


def _parse_vina_score(text: str) -> float:
    for line in text.splitlines():
        if "REMARK VINA RESULT" in line.upper() or line.strip().startswith("1 "):
            parts = line.split()
            for part in parts:
                try:
                    val = float(part)
                    if -20 < val < 5:
                        return val
                except ValueError:
                    continue
    return 0.0


def dock_molecule(
    smiles: str,
    target_slug: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    exhaustiveness: int,
    seed: int,
    receptor_path: Path | None = None,
) -> tuple[float, str, str]:
    """Return (score, pose_text, engine)."""
    pdb = smiles_to_pdb_block(smiles)
    if pdb and vina_available():
        result = run_vina(pdb, receptor_path, center, size, exhaustiveness, seed)
        if result:
            return result[0], result[1], "autodock-vina"
    pose = pdb or f"REMARK heuristic pose for {target_slug}\nEND\n"
    return heuristic_score(smiles, target_slug, seed), pose, "heuristic-v0"
