"""RDKit wrappers for validation, descriptors, fingerprints, and search."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from io import BytesIO, StringIO
from typing import Any

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import (
    Crippen,
    Descriptors,
    Lipinski,
    QED,
    rdMolDescriptors,
)
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem import inchi as rd_inchi

RDLogger.DisableLog("rdApp.*")

FP_RADIUS = 2
FP_BITS = 2048


@dataclass
class DescriptorsResult:
    mw: float
    logp: float
    tpsa: float
    hbd: int
    hba: int
    rotatable_bonds: int
    ring_count: int
    lipinski_pass: bool
    veber_pass: bool
    qed: float
    formula: str


@dataclass
class ParsedMolecule:
    smiles_raw: str
    canonical_smiles: str
    inchikey: str
    name: str
    source_row: int | None
    error: str | None = None


def mol_from_smiles(smiles: str) -> Chem.Mol | None:
    if not smiles or not smiles.strip():
        return None
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        return None
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        return None
    return mol


def canonicalize(smiles: str) -> str | None:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)


def inchikey_for(mol: Chem.Mol) -> str:
    try:
        return rd_inchi.MolToInchiKey(mol) or ""
    except Exception:
        return hashlib.sha1(Chem.MolToSmiles(mol, canonical=True).encode()).hexdigest()[:27]


def parse_smiles(smiles: str, name: str = "", source_row: int | None = None) -> ParsedMolecule:
    raw = smiles.strip()
    mol = mol_from_smiles(raw)
    if mol is None:
        return ParsedMolecule(raw, "", "", name, source_row, error="unparseable SMILES")
    can = Chem.MolToSmiles(mol, canonical=True)
    return ParsedMolecule(raw, can, inchikey_for(mol), name, source_row)


def compute_descriptors(mol: Chem.Mol) -> DescriptorsResult:
    mw = float(Descriptors.MolWt(mol))
    logp = float(Crippen.MolLogP(mol))
    tpsa = float(rdMolDescriptors.CalcTPSA(mol))
    hbd = int(Lipinski.NumHDonors(mol))
    hba = int(Lipinski.NumHAcceptors(mol))
    rot = int(Lipinski.NumRotatableBonds(mol))
    rings = int(rdMolDescriptors.CalcNumRings(mol))
    lipinski = mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10
    veber = rot <= 10 and tpsa <= 140
    try:
        qed = float(QED.qed(mol))
    except Exception:
        qed = 0.0
    formula = rdMolDescriptors.CalcMolFormula(mol)
    return DescriptorsResult(
        mw=round(mw, 3),
        logp=round(logp, 3),
        tpsa=round(tpsa, 3),
        hbd=hbd,
        hba=hba,
        rotatable_bonds=rot,
        ring_count=rings,
        lipinski_pass=lipinski,
        veber_pass=veber,
        qed=round(qed, 4),
        formula=formula,
    )


def descriptors_from_smiles(smiles: str) -> dict[str, Any] | None:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return None
    return asdict(compute_descriptors(mol))


def morgan_fp(mol: Chem.Mol):
    return rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, FP_RADIUS, nBits=FP_BITS)


def fp_to_bytes(fp) -> bytes:
    return DataStructs.BitVectToBinaryText(fp)


def fp_from_bytes(data: bytes):
    return DataStructs.CreateFromBinaryText(data)


def tanimoto(fp_a, fp_b) -> float:
    return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))


def tanimoto_bytes(a: bytes, b: bytes) -> float:
    return tanimoto(fp_from_bytes(a), fp_from_bytes(b))


def depict_svg(smiles: str, width: int = 280, height: int = 200) -> str:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='280' height='200'><text x='12' y='24'>Invalid</text></svg>"
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    opts = drawer.drawOptions()
    opts.clearBackground = False
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def substructure_match(query_smarts: str, smiles: str) -> bool:
    q = Chem.MolFromSmarts(query_smarts)
    mol = mol_from_smiles(smiles)
    if q is None or mol is None:
        return False
    return mol.HasSubstructMatch(q)


def parse_smiles_table(text: str) -> list[ParsedMolecule]:
    """Parse a SMILES file: smiles[ whitespace name] per line."""
    out: list[ParsedMolecule] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace(",", " ").split()
        smiles = parts[0]
        name = " ".join(parts[1:]) if len(parts) > 1 else f"mol_{i}"
        out.append(parse_smiles(smiles, name=name, source_row=i))
    return out


def parse_csv_rows(
    text: str, smiles_col: str, name_col: str | None = None
) -> list[ParsedMolecule]:
    import csv

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        return []
    fields = {f.lower(): f for f in reader.fieldnames}
    smiles_key = fields.get(smiles_col.lower(), smiles_col)
    name_key = fields.get((name_col or "name").lower()) if name_col or "name" in fields else None
    out: list[ParsedMolecule] = []
    for i, row in enumerate(reader, start=2):
        smiles = (row.get(smiles_key) or "").strip()
        name = (row.get(name_key) or "").strip() if name_key else f"row_{i}"
        if not smiles:
            out.append(ParsedMolecule("", "", "", name, i, error="empty SMILES"))
            continue
        out.append(parse_smiles(smiles, name=name or f"row_{i}", source_row=i))
    return out


def parse_sdf(data: bytes) -> list[ParsedMolecule]:
    suppl = Chem.ForwardSDMolSupplier(BytesIO(data), sanitize=False)
    out: list[ParsedMolecule] = []
    for i, mol in enumerate(suppl, start=1):
        if mol is None:
            out.append(ParsedMolecule("", "", "", f"sdf_{i}", i, error="unparseable SDF record"))
            continue
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            out.append(ParsedMolecule("", "", "", f"sdf_{i}", i, error="sanitize failed"))
            continue
        name = mol.GetProp("_Name") if mol.HasProp("_Name") else f"sdf_{i}"
        can = Chem.MolToSmiles(mol, canonical=True)
        out.append(ParsedMolecule(can, can, inchikey_for(mol), name or f"sdf_{i}", i))
    return out


def write_sdf(rows: list[dict[str, Any]]) -> bytes:
    buf = BytesIO()
    writer = Chem.SDWriter(buf)
    for row in rows:
        mol = mol_from_smiles(row.get("canonical_smiles") or row.get("smiles") or "")
        if mol is None:
            continue
        if row.get("name"):
            mol.SetProp("_Name", str(row["name"]))
        for key, value in row.items():
            if key in {"canonical_smiles", "smiles", "name"} or value is None:
                continue
            mol.SetProp(str(key), str(value))
        writer.write(mol)
    writer.close()
    return buf.getvalue()


def params_hash(payload: dict[str, Any]) -> str:
    blob = repr(sorted((k, payload[k]) for k in payload)).encode()
    return hashlib.sha256(blob).hexdigest()


def smiles_to_pdb_block(smiles: str) -> str | None:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    try:
        from rdkit.Chem import AllChem

        AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
        AllChem.UFFOptimizeMolecule(mol, maxIters=200)
    except Exception:
        return None
    return Chem.MolToPDBBlock(mol)
