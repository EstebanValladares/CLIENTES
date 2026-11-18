"""Consulta de órdenes de compra sincronizadas en la base local de Control de Pagos."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR.parent / "CONTROL_PAGOS_OC" / "datos" / "ecosistema_oc.db"


class OrdenesCompraService:
    @classmethod
    def buscar_por_folio(cls, obra: str, folio: str, limite: int = 100) -> Dict[str, Any]:
        obra_clean = str(obra).strip().upper()
        folio_clean = str(folio).strip().upper()
        if not obra_clean or not folio_clean:
            raise ValueError("Debe proporcionar la obra y el folio de la orden de compra.")
        if not DB_PATH.is_file():
            raise FileNotFoundError(f"No se encontró la base local de órdenes de compra: {DB_PATH}")

        escaped_folio = folio_clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        connection_uri = f"file:{quote(DB_PATH.resolve().as_posix(), safe='/:')}?mode=ro"

        try:
            with sqlite3.connect(connection_uri, uri=True, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT empresa, centro_costos, numero_oc, fecha, proveedor, total,
                           estatus, id_ek10, actualizado_en, tipo_sugerido, rubro_sugerido
                    FROM ordenes_compra_ek9
                    WHERE UPPER(centro_costos) = ?
                      AND UPPER(centro_costos || '-' || printf('%08d', numero_oc)) LIKE ? ESCAPE '\\'
                    ORDER BY fecha DESC, numero_oc DESC
                    LIMIT ?
                    """,
                    (obra_clean, f"%{escaped_folio}%", max(1, min(int(limite), 100))),
                ).fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError(f"No se pudieron consultar las órdenes de compra locales: {exc}") from exc

        ordenes: List[Dict[str, Any]] = []
        for row in rows:
            orden = dict(row)
            centro_costos = str(orden["centro_costos"] or "").strip().upper()
            numero_oc = int(orden["numero_oc"] or 0)
            orden["folio"] = f"{centro_costos}-{numero_oc:08d}"
            orden["tipo_origen"] = None
            ordenes.append(orden)

        return {
            "ok": True,
            "obra": obra_clean,
            "folio_buscado": folio_clean,
            "origen_datos": "Copia local de Control de Pagos (SQLite)",
            "tipo_origen_disponible": False,
            "total": len(ordenes),
            "ordenes_compra": ordenes,
        }
