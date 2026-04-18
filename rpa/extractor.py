"""
RPA - Extracción de datos: Distribución de Cartera por Producto
Fuente: datos.gov.co | Dataset: rvii-eis8
Autor: Candidato Prueba Técnica - Visión Gerencial
"""

import sys
import os
import requests
import psycopg2
import logging
from datetime import datetime
from dotenv import load_dotenv

# Windows: forzar UTF-8 antes de cualquier otra cosa
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# ──────────────────────────────────────────────
# Configuración de logging — UTF-8 explícito
# en consola y archivo para compatibilidad Windows
# ──────────────────────────────────────────────
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_fmt)

_file_handler = logging.FileHandler("rpa_extractor.log", encoding="utf-8")
_file_handler.setFormatter(_fmt)

log = logging.getLogger("extractor")
log.setLevel(logging.INFO)
log.addHandler(_console_handler)
log.addHandler(_file_handler)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
DATASET_URL = "https://www.datos.gov.co/resource/rvii-eis8.json"
LIMIT       = 50_000


# ──────────────────────────────────────────────
# Funciones de extracción
# ──────────────────────────────────────────────
def fetch_batch(offset: int = 0) -> list:
    """Descarga un bloque de registros como bytes y decodifica manualmente en UTF-8."""
    params = {
        "$limit":  LIMIT,
        "$offset": offset,
        "$order":  "fecha_corte DESC"
    }
    response = requests.get(DATASET_URL, params=params, timeout=60)
    response.raise_for_status()
    # Decodificar bytes crudos en UTF-8 — ignorar bytes inválidos
    import json
    texto = response.content.decode("utf-8", errors="replace")
    return json.loads(texto)


def fetch_all_records() -> list:
    """Pagina la API hasta obtener todos los registros disponibles."""
    all_records = []
    offset = 0

    while True:
        log.info(f"Descargando registros: offset={offset}")
        batch = fetch_batch(offset)

        if not batch:
            log.info("No hay mas registros. Extraccion completa.")
            break

        all_records.extend(batch)
        log.info(f"Total acumulado: {len(all_records)} registros")
        offset += LIMIT

        if len(batch) < LIMIT:
            break

    return all_records


# ──────────────────────────────────────────────
# Funciones de base de datos
# ──────────────────────────────────────────────
def get_connection():
    """Retorna conexion a PostgreSQL con parametros separados (evita problemas de encoding en el DSN)."""
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "cartera_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "12345")
    )
    conn.set_client_encoding("UTF8")
    return conn


def clean_str(value) -> str | None:
    """Limpia un string garantizando compatibilidad UTF-8."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        value = str(value)
    # Eliminar caracteres de reemplazo Unicode (U+FFFD) que puso errors='replace'
    return value.replace("\ufffd", "").strip() or None


def safe_float(value) -> float | None:
    """Convierte a float de forma segura."""
    try:
        return float(value) if value not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None


def safe_int(value) -> int | None:
    """Convierte a entero de forma segura."""
    try:
        return int(value) if value not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None


def insert_records(records: list) -> int:
    """Inserta registros en la tabla cartera. Retorna filas insertadas."""
    conn = get_connection()
    cur  = conn.cursor()
    inserted = 0

    for r in records:
        try:
            cur.execute("""
                INSERT INTO cartera (
                    tipo_entidad, codigo_entidad, nombreentidad,
                    fecha_corte, unicap, descrip_uc,
                    renglon, desc_renglon,
                    saldo_total, vigente,
                    vencida_1_2_meses, vencida_2_3_meses,
                    vencida_1_3_meses, vencida_3_4_meses,
                    vencida_4_meses, vencida_3_6_meses,
                    vencida_6_meses, vencida_1_4_meses,
                    vencida_4_6_meses, vencida_6_12_meses,
                    vencida_12_18_meses, vencida_12_meses,
                    vencida_18_meses, num_clientes_mora
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                )
                ON CONFLICT DO NOTHING;
            """, (
                safe_int(r.get("tipo_entidad")),
                safe_int(r.get("codigo_entidad")),
                clean_str(r.get("nombreentidad")),
                r.get("fecha_corte"),
                safe_int(r.get("unicap")),
                clean_str(r.get("descrip_uc")),
                safe_int(r.get("renglon")),
                clean_str(r.get("desc_renglon")),
                safe_float(r.get("_1_saldo_de_la_cartera_a")),
                safe_float(r.get("_2_vigente")),
                safe_float(r.get("_3_vencida_1_2_meses")),
                safe_float(r.get("_4_vencida_2_3_meses")),
                safe_float(r.get("_5_vencida_1_3_meses")),
                safe_float(r.get("_6_vencida_3_4_meses")),
                safe_float(r.get("_7_vencida_de_4_meses")),
                safe_float(r.get("_8_vencida_3_6_meses")),
                safe_float(r.get("_9_vencida_6_meses")),
                safe_float(r.get("_10_vencida_1_4_meses")),
                safe_float(r.get("_11_vencida_4_6_meses")),
                safe_float(r.get("_12_vencida_6_12_meses")),
                safe_float(r.get("_13_vencida_12_18_meses")),
                safe_float(r.get("_14_vencida_12_meses")),
                safe_float(r.get("_15_vencida_18_meses")),
                safe_int(r.get("_16_n_mero_de_clientes_mora")),
            ))
            inserted += 1
        except Exception as e:
            log.warning(f"Error insertando registro: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()
    return inserted


# ──────────────────────────────────────────────
# Punto de entrada
# ──────────────────────────────────────────────
if __name__ == "__main__":
    start = datetime.now()
    log.info("=" * 50)
    log.info("Iniciando RPA - Extraccion Cartera Financiera")
    log.info("=" * 50)

    try:
        records = fetch_all_records()
        log.info(f"Registros descargados: {len(records)}")

        count = insert_records(records)
        log.info(f"Registros insertados en DB: {count}")

    except requests.RequestException as e:
        log.error(f"Error HTTP: {e}")
    except psycopg2.Error as e:
        log.error(f"Error PostgreSQL: {e}")
    except Exception as e:
        log.error(f"Error inesperado: {e}")
    finally:
        elapsed = datetime.now() - start
        log.info(f"Tiempo total: {elapsed}")
        log.info("=" * 50)