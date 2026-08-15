from opengero.chemistry import (
    canonicalize,
    compute_descriptors,
    mol_from_smiles,
    parse_csv_rows,
    parse_smiles,
    parse_smiles_table,
    substructure_match,
    tanimoto,
    morgan_fp,
)
from opengero.docking import heuristic_score


def test_canonicalize_and_inchikey():
    a = parse_smiles("CCO", name="ethanol")
    b = parse_smiles("OCC", name="ethanol-reorder")
    assert a.error is None
    assert a.canonical_smiles == b.canonical_smiles
    assert a.inchikey == b.inchikey
    assert len(a.inchikey) == 27


def test_invalid_smiles():
    parsed = parse_smiles("not-a-molecule")
    assert parsed.error


def test_lipinski_and_veber_aspirin():
    mol = mol_from_smiles("CC(=O)Oc1ccccc1C(=O)O")
    desc = compute_descriptors(mol)
    assert 170 < desc.mw < 190
    assert desc.lipinski_pass is True
    assert desc.veber_pass is True
    assert desc.hbd >= 1
    assert desc.formula.startswith("C")


def test_tanimoto_identical_is_one():
    mol = mol_from_smiles("CCO")
    fp = morgan_fp(mol)
    assert tanimoto(fp, fp) == 1.0


def test_substructure_phenol():
    assert substructure_match("c1ccccc1O", "Oc1ccc(/C=C/c2cc(O)cc(O)c2)cc1")
    assert not substructure_match("c1ccccc1O", "CCO")


def test_parse_smiles_table_and_csv():
    rows = parse_smiles_table("CCO ethanol\nnot-valid junk\n")
    assert rows[0].name == "ethanol"
    assert rows[1].error
    csv_rows = parse_csv_rows("smiles,name\nCCO,ethanol\n", smiles_col="smiles", name_col="name")
    assert csv_rows[0].canonical_smiles == canonicalize("CCO")


def test_heuristic_docking_is_deterministic():
    a = heuristic_score("CCO", "mtor", 42)
    b = heuristic_score("CCO", "mtor", 42)
    c = heuristic_score("CCO", "mtor", 99)
    assert a == b
    assert a != c
