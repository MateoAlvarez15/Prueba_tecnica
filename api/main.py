"""
API REST - Distribución de Cartera Financiera Colombia
Fuente de datos: datos.gov.co | Dataset: rvii-eis8
Autor: Candidato Prueba Técnica - Visión Gerencial
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# ──────────────────────────────────────────────
# Aplicación FastAPI
# ──────────────────────────────────────────────
app = FastAPI(
    title="API - Distribución de Cartera Financiera",
    description=(
        "Consulta la distribución de cartera de las entidades financieras "
        "colombianas reportadas en datos.gov.co. Filtra por entidad y tipo de cartera."
    ),
    version="1.0.0",
    contact={"name": "Prueba Técnica - Visión Gerencial"}
)

# CORS: permitir todos los orígenes (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Utilidades de DB
# ──────────────────────────────────────────────
def get_connection():
    """Crea y retorna una conexión a PostgreSQL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL no configurada.")
    return psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)


def query_db(sql: str, params: tuple = ()) -> list[dict]:
    """Ejecuta una consulta y retorna los resultados como lista de dicts."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    """Endpoint raíz — verifica que la API está activa."""
    return {
        "status": "ok",
        "mensaje": "API de Distribución de Cartera Financiera Colombia",
        "version": "1.0.0",
        "endpoints": ["/cartera", "/entidades", "/tipos-cartera", "/resumen"]
    }


@app.get("/cartera", tags=["Cartera"])
def get_cartera(
    entidad: str = Query(..., description="Nombre (parcial) de la entidad financiera"),
    tipo_cartera: Optional[str] = Query(None, description="Tipo de cartera (ej: LIBRE INVERSIÓN, TARJETAS DE CRÉDITO)"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio formato YYYY-MM-DD"),
    fecha_fin: Optional[str]    = Query(None, description="Fecha fin formato YYYY-MM-DD"),
    limit: int = Query(500, ge=1, le=5000, description="Máximo de registros a retornar")
):
    """
    Consulta la cartera filtrada por **entidad** y opcionalmente por **tipo de cartera**.

    - Busca coincidencia parcial en el nombre de la entidad (case-insensitive).
    - Se puede agregar rango de fechas de corte.
    """
    sql = """
        SELECT
            nombreentidad       AS entidad,
            descrip_uc          AS tipo_cartera,
            desc_renglon        AS producto,
            fecha_corte,
            saldo_total,
            vigente,
            (COALESCE(vencida_1_2_meses,0)  + COALESCE(vencida_2_3_meses,0)
           + COALESCE(vencida_1_3_meses,0)  + COALESCE(vencida_3_4_meses,0)
           + COALESCE(vencida_4_meses,0)    + COALESCE(vencida_3_6_meses,0)
           + COALESCE(vencida_6_meses,0)    + COALESCE(vencida_1_4_meses,0)
           + COALESCE(vencida_4_6_meses,0)  + COALESCE(vencida_6_12_meses,0)
           + COALESCE(vencida_12_18_meses,0)+ COALESCE(vencida_12_meses,0)
           + COALESCE(vencida_18_meses,0))  AS total_vencida,
            num_clientes_mora
        FROM cartera
        WHERE nombreentidad ILIKE %s
    """
    params: list = [f"%{entidad}%"]

    if tipo_cartera:
        sql += " AND descrip_uc ILIKE %s"
        params.append(f"%{tipo_cartera}%")

    if fecha_inicio:
        sql += " AND fecha_corte >= %s"
        params.append(fecha_inicio)

    if fecha_fin:
        sql += " AND fecha_corte <= %s"
        params.append(fecha_fin)

    sql += " ORDER BY fecha_corte DESC, saldo_total DESC LIMIT %s"
    params.append(limit)

    rows = query_db(sql, tuple(params))

    if not rows:
        raise HTTPException(status_code=404, detail="No se encontraron registros con los filtros dados.")

    return {"total": len(rows), "filtros": {"entidad": entidad, "tipo_cartera": tipo_cartera}, "data": rows}


@app.get("/entidades", tags=["Catálogos"])
def get_entidades(q: Optional[str] = Query(None, description="Filtro parcial del nombre")):
    """Lista todas las entidades financieras disponibles en la base de datos."""
    sql = "SELECT DISTINCT nombreentidad, codigo_entidad, tipo_entidad FROM cartera"
    params: tuple = ()

    if q:
        sql += " WHERE nombreentidad ILIKE %s"
        params = (f"%{q}%",)

    sql += " ORDER BY nombreentidad"
    return query_db(sql, params)


@app.get("/tipos-cartera", tags=["Catálogos"])
def get_tipos_cartera():
    """Lista todos los tipos de cartera disponibles."""
    sql = "SELECT DISTINCT unicap, descrip_uc FROM cartera ORDER BY unicap"
    return query_db(sql)


@app.get("/resumen", tags=["Análisis"])
def get_resumen(
    entidad: Optional[str] = Query(None, description="Filtrar por entidad"),
    tipo_cartera: Optional[str] = Query(None, description="Filtrar por tipo de cartera")
):
    """
    Retorna un resumen agregado por tipo de cartera:
    saldo total, cartera vigente, total vencida y número de clientes en mora.
    """
    sql = """
        SELECT
            descrip_uc                      AS tipo_cartera,
            COUNT(*)                        AS num_registros,
            SUM(saldo_total)                AS saldo_total,
            SUM(vigente)                    AS total_vigente,
            SUM(
                COALESCE(vencida_1_2_meses,0)  + COALESCE(vencida_2_3_meses,0)
              + COALESCE(vencida_1_3_meses,0)  + COALESCE(vencida_3_4_meses,0)
              + COALESCE(vencida_4_meses,0)    + COALESCE(vencida_3_6_meses,0)
              + COALESCE(vencida_6_meses,0)
            )                               AS total_vencida,
            SUM(num_clientes_mora)          AS clientes_en_mora
        FROM cartera
        WHERE 1=1
    """
    params: list = []

    if entidad:
        sql += " AND nombreentidad ILIKE %s"
        params.append(f"%{entidad}%")

    if tipo_cartera:
        sql += " AND descrip_uc ILIKE %s"
        params.append(f"%{tipo_cartera}%")

    sql += " GROUP BY descrip_uc ORDER BY saldo_total DESC"
    return query_db(sql, tuple(params))
