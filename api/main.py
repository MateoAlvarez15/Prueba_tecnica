"""
API REST - Distribución de Cartera Financiera Colombia
Fuente de datos: datos.gov.co | Dataset: rvii-eis8
Autor: Candidato Prueba Técnica - Visión Gerencial
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg
from psycopg.rows import dict_row
import os
import logging
from dotenv import load_dotenv
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
import json

load_dotenv()

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# Encoder personalizado para convertir tipos de PostgreSQL (Decimal, datetime)
# que el encoder estándar de Python no soporta al serializar a JSON.
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)
    
# Serializa los datos de la DB a JSON usando el encoder personalizado.
def jsonify(data):
    """Serializa datos con soporte para Decimal y datetime."""
    return json.loads(json.dumps(data, cls=CustomEncoder))


# ──────────────────────────────────────────────
# App
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# Crea y retorna una conexión activa a PostgreSQL.
# Lee DATABASE_URL del entorno y usa dict_row para que cada fila
# sea un diccionario en lugar de una tupla.
def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL no configurada.")
    return psycopg.connect(db_url, row_factory=dict_row)

# Ejecuta una consulta SQL con parámetros y retorna los resultados
# como lista de diccionarios. Cierra la conexión al terminar.
def query_db(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        log.error(f"Error en consulta DB: {e}")
        raise HTTPException(status_code=500, detail="Error interno en la base de datos.")
    finally:
        conn.close()



# Endpoint raíz — confirma que la API está activa y lista.
# Retorna el mapa de todos los endpoints disponibles.
@app.get("/", tags=["Info"])
def root():
    """Verifica que la API está activa y lista."""
    return {
        "status": "ok",
        "api": "Distribución de Cartera Financiera Colombia",
        "version": "1.0.0",
        "endpoints": {
            "cartera":       "/cartera?entidad=Bancolombia&tipo_cartera=LIBRANZA",
            "entidades":     "/entidades",
            "tipos_cartera": "/tipos-cartera",
            "resumen":       "/resumen",
            "tendencia":     "/tendencia?entidad=Bancolombia"
        }
    }


# Consulta principal de cartera filtrada por entidad.
# Permite filtrar además por tipo de cartera y rango de fechas.
# Implementa paginación para manejar grandes volúmenes de datos.
@app.get("/cartera", tags=["Cartera"])
def get_cartera(
    entidad:      str           = Query(...,   description="Nombre (parcial) de la entidad financiera"),
    tipo_cartera: Optional[str] = Query(None,  description="Tipo de cartera (ej: LIBRE INVERSION)"),
    fecha_inicio: Optional[str] = Query(None,  description="Fecha inicio YYYY-MM-DD"),
    fecha_fin:    Optional[str] = Query(None,  description="Fecha fin YYYY-MM-DD"),
    page:         int           = Query(1,  ge=1,           description="Página"),
    page_size:    int           = Query(100, ge=1, le=1000, description="Registros por página")
):
    """
    Consulta cartera filtrada por **entidad** y opcionalmente **tipo de cartera**.
    Soporta paginación con `page` y `page_size`.
    """
    offset = (page - 1) * page_size

    base_sql = """
        FROM cartera
        WHERE nombreentidad ILIKE %s
    """
    params: list = [f"%{entidad}%"]

    if tipo_cartera:
        base_sql += " AND descrip_uc ILIKE %s"
        params.append(f"%{tipo_cartera}%")
    if fecha_inicio:
        base_sql += " AND fecha_corte >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        base_sql += " AND fecha_corte <= %s"
        params.append(fecha_fin)

    total_rows = query_db(f"SELECT COUNT(*) {base_sql}", tuple(params))[0]["count"]

    select_sql = f"""
        SELECT
            nombreentidad                           AS entidad,
            codigo_entidad,
            tipo_entidad,
            descrip_uc                              AS tipo_cartera,
            desc_renglon                            AS producto,
            fecha_corte,
            saldo_total,
            vigente,
            (
                COALESCE(vencida_1_2_meses,  0) + COALESCE(vencida_2_3_meses,  0) +
                COALESCE(vencida_1_3_meses,  0) + COALESCE(vencida_3_4_meses,  0) +
                COALESCE(vencida_4_meses,    0) + COALESCE(vencida_3_6_meses,  0) +
                COALESCE(vencida_6_meses,    0) + COALESCE(vencida_1_4_meses,  0) +
                COALESCE(vencida_4_6_meses,  0) + COALESCE(vencida_6_12_meses, 0) +
                COALESCE(vencida_12_18_meses,0) + COALESCE(vencida_12_meses,   0) +
                COALESCE(vencida_18_meses,   0)
            )                                       AS total_vencida,
            num_clientes_mora
        {base_sql}
        ORDER BY fecha_corte DESC, saldo_total DESC
        LIMIT %s OFFSET %s
    """
    rows = query_db(select_sql, tuple(params) + (page_size, offset))

    if not rows:
        raise HTTPException(status_code=404, detail="No se encontraron registros con los filtros dados.")

    return JSONResponse(content=jsonify({
        "paginacion": {
            "page":    page,
            "page_size": page_size,
            "total":   total_rows,
            "paginas": -(-int(total_rows) // page_size)
        },
        "filtros": {"entidad": entidad, "tipo_cartera": tipo_cartera},
        "data": rows
    }))


# Retorna el catálogo completo de entidades financieras en la DB.
# Útil para conocer los nombres exactos antes de consultar /cartera.
@app.get("/entidades", tags=["Catálogos"])
def get_entidades(q: Optional[str] = Query(None, description="Búsqueda parcial")):
    """Lista todas las entidades financieras disponibles."""
    sql = "SELECT DISTINCT nombreentidad, codigo_entidad, tipo_entidad FROM cartera"
    params: tuple = ()
    if q:
        sql += " WHERE nombreentidad ILIKE %s"
        params = (f"%{q}%",)
    sql += " ORDER BY nombreentidad"
    return JSONResponse(content=jsonify(query_db(sql, params)))


# Retorna el catálogo de tipos de cartera disponibles en la DB.
# Muestra el código interno (unicap) y la descripción legible (descrip_uc).
@app.get("/tipos-cartera", tags=["Catálogos"])
def get_tipos_cartera():
    """Lista todos los tipos de cartera disponibles."""
    return JSONResponse(content=jsonify(
        query_db("SELECT DISTINCT unicap, descrip_uc FROM cartera ORDER BY unicap")
    ))


# Retorna un resumen agregado de saldos agrupado por tipo de cartera.
# Consolida saldo total, cartera vigente, vencida y clientes en mora.
# Ideal para KPIs y comparación entre productos financieros.
@app.get("/resumen", tags=["Análisis"])
def get_resumen(
    entidad:      Optional[str] = Query(None, description="Filtrar por entidad"),
    tipo_cartera: Optional[str] = Query(None, description="Filtrar por tipo de cartera")
):
    """Resumen agregado por tipo de cartera: saldo total, vigente, vencida y mora."""
    sql = """
        SELECT
            descrip_uc                  AS tipo_cartera,
            COUNT(*)                    AS num_registros,
            SUM(saldo_total)            AS saldo_total,
            SUM(vigente)                AS total_vigente,
            SUM(
                COALESCE(vencida_1_2_meses,0) + COALESCE(vencida_2_3_meses,0) +
                COALESCE(vencida_1_3_meses,0) + COALESCE(vencida_3_4_meses,0) +
                COALESCE(vencida_4_meses,0)   + COALESCE(vencida_3_6_meses,0) +
                COALESCE(vencida_6_meses,0)
            )                           AS total_vencida,
            SUM(num_clientes_mora)      AS clientes_en_mora
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
    sql += " GROUP BY descrip_uc ORDER BY saldo_total DESC NULLS LAST"
    return JSONResponse(content=jsonify(query_db(sql, tuple(params))))


# Verifica el estado de la API y la conexión a la base de datos.
# Retorna si la DB está conectada y el total de registros disponibles.
@app.get("/health", tags=["Info"])
def health():
    """
    Verifica el estado de la API y la conexión a la base de datos.
    
    Returns:
        dict: Estado de la API y de la DB.
    """
    try:
        query_db("SELECT 1")
        return {"status": "ok", "database": "connected", "records": query_db("SELECT COUNT(*) as total FROM cartera")[0]["total"]}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "detail": str(e)}


# Retorna la evolución mensual del saldo agrupado por periodo y tipo de cartera.
# Diseñado para alimentar gráficas de tendencia en Power BI.
@app.get("/tendencia", tags=["Análisis"])
def get_tendencia(
    entidad:      Optional[str] = Query(None, description="Filtrar por entidad"),
    tipo_cartera: Optional[str] = Query(None, description="Filtrar por tipo de cartera")
):
    """
    Evolución mensual del saldo total agrupado por fecha de corte y tipo de cartera.
    Ideal para gráficas de tendencia en Power BI.
    """
    sql = """
        SELECT
            DATE_TRUNC('month', fecha_corte)    AS periodo,
            descrip_uc                          AS tipo_cartera,
            SUM(saldo_total)                    AS saldo_total,
            SUM(vigente)                        AS total_vigente,
            SUM(num_clientes_mora)              AS clientes_en_mora
        FROM cartera
        WHERE fecha_corte IS NOT NULL
    """
    params: list = []
    if entidad:
        sql += " AND nombreentidad ILIKE %s"
        params.append(f"%{entidad}%")
    if tipo_cartera:
        sql += " AND descrip_uc ILIKE %s"
        params.append(f"%{tipo_cartera}%")
    sql += " GROUP BY periodo, descrip_uc ORDER BY periodo ASC"
    return JSONResponse(content=jsonify(query_db(sql, tuple(params))))