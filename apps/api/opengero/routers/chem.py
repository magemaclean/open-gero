from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from ..chemistry import depict_svg, descriptors_from_smiles, parse_smiles

router = APIRouter(prefix="/api/chem", tags=["chem"])


class SmilesIn(BaseModel):
    smiles: str


@router.post("/properties")
def properties(body: SmilesIn):
    parsed = parse_smiles(body.smiles)
    if parsed.error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, parsed.error)
    desc = descriptors_from_smiles(parsed.canonical_smiles)
    return {
        "canonical_smiles": parsed.canonical_smiles,
        "inchikey": parsed.inchikey,
        "properties": desc,
    }


@router.get("/depict")
def depict(smiles: str, width: int = 280, height: int = 200):
    svg = depict_svg(smiles, width=width, height=height)
    return Response(content=svg, media_type="image/svg+xml")
