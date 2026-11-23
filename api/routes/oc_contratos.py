"""
API Route: Trazabilidad OC, Contratos & Insumos (Enkontrol / Aryve SOC)
Permite buscar por Folio de OC, Clave de Contrato (ej. ELEC, MYM, PLOM) o Número + Obra.
"""

from fastapi import APIRouter, Query
from typing import Optional
from core.oc_contrato_service import OcContratoService

router = APIRouter(prefix="/api/oc-contratos", tags=["OC y Contratos"])


@router.get("/consultar")
def consultar_oc(
    folio: Optional[str] = Query(None, description="Folio completo (ej. KBN-00000014), número de OC (ej. 14) o Clave"),
    clave: Optional[str] = Query(None, description="Clave de contrato (ej. ELEC, MYM, PLOM, SUB SANIT)"),
    obra: Optional[str] = Query(None, description="Clave de obra o centro de costos (ej. KBN)"),
    compania: Optional[int] = Query(None, description="ID de compañía (1 = Aryve, 2 = Velas)")
):
    """Retorna la ficha integral de la OC con su contrato, estimación e insumos."""
    return OcContratoService.consultar(folio=folio, clave=clave, obra=obra, compania=compania)
