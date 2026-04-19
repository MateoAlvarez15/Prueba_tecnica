# 📊 Distribución de Cartera Financiera — Colombia

![Python](https://img.shields.io/badge/Python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue)
![Render](https://img.shields.io/badge/Deploy-Render-purple)
![Status](https://img.shields.io/badge/API-Live-brightgreen)

Solución completa para extraer, almacenar, exponer y visualizar los datos de distribución de cartera de las entidades financieras colombianas publicados en [datos.gov.co](https://www.datos.gov.co/Hacienda-y-Cr-dito-P-blico/Distribuci-n-de-cartera-por-producto/rvii-eis8/about_data).



---

## Arquitectura

```
datos.gov.co (API Socrata)
        │
        ▼
  rpa/extractor.py          ← Descarga y pagina 107.721 registros
        │
        ▼
  PostgreSQL (Render Cloud) ← Almacenamiento persistente en la nube
        │
        ▼
  api/main.py (FastAPI)     ← API REST pública con 6 endpoints
        │
        ▼
  Power BI Dashboard        ← Análisis visual con filtros interactivos
```

---

## Estructura del proyecto

```
Prueba_tecnica/
├── rpa/
│   ├── extractor.py        # RPA: descarga y carga los datos
│   └── diagnostico.py      # Herramienta de diagnóstico de encoding
├── api/
│   ├── main.py             # API REST con FastAPI
│   └── requirements.txt
├── db/
│   └── schema.sql          # Tabla e índices en PostgreSQL
├── dashboard/
│   └── Cartera_Financiera.pbix
├── .gitignore
└── README.md
```

---

## Instalación y configuración

### Requisitos
- Python 3.14+
- PostgreSQL 16+
- Power BI Desktop

### Variables de entorno

**RPA (local):**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cartera_db
DB_USER=postgres
DB_PASSWORD=tu_password
```

**API (Render):**
```env
DATABASE_URL=postgresql://usuario:password@host:5432/nombre_db
```

### Crear la base de datos

```bash
psql -U postgres -d cartera_db -f db/schema.sql
```

---

## RPA — Extracción de datos

```bash
cd rpa
pip install -r requirements.txt

# Windows
$env:DATABASE_URL="postgresql://..."
python extractor.py
```

Características del extractor:
- Paginación automática en bloques de 50.000 registros
- Logging a consola y archivo rpa_extractor.log
- Conversión segura de tipos con safe_float, safe_int, clean_str
- Compatible con Python 3.14 usando psycopg3
- ON CONFLICT DO NOTHING para evitar duplicados

Resultado: 107.721 registros insertados en 25 segundos.

---

## API REST — Endpoints

URL base: https://prueba-tecnica-api-gsrr.onrender.com

Documentación interactiva: https://prueba-tecnica-api-gsrr.onrender.com/docs

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | / | Estado de la API |
| GET | /health | Estado de la API y conexión a DB |
| GET | /entidades | Catálogo de entidades financieras |
| GET | /tipos-cartera | Catálogo de tipos de cartera |
| GET | /cartera | Consulta por entidad y tipo de cartera |
| GET | /resumen | Agregados por tipo de cartera |
| GET | /tendencia | Evolución mensual del saldo |

### Ejemplos de uso

```bash
# Estado de la API
curl https://prueba-tecnica-api-gsrr.onrender.com/health

# Listar entidades
curl https://prueba-tecnica-api-gsrr.onrender.com/entidades

# Cartera de Bancolombia tipo Libranza
curl "https://prueba-tecnica-api-gsrr.onrender.com/cartera?entidad=Bancolombia&tipo_cartera=LIBRANZA"

# Resumen por tipo de cartera
curl https://prueba-tecnica-api-gsrr.onrender.com/resumen

# Tendencia mensual
curl "https://prueba-tecnica-api-gsrr.onrender.com/tendencia?tipo_cartera=LIBRANZA"
```

### Ejemplo de respuesta /resumen

```json
[
  {
    "tipo_cartera": "LIBRANZA",
    "num_registros": 8652,
    "saldo_total": 15509652509831262,
    "total_vigente": 15107036532414798,
    "total_vencida": 402615991099478,
    "clientes_en_mora": 17280912
  }
]
```

---

## Power BI Dashboard

Conectado directamente a PostgreSQL en Render.

Visualizaciones:
- 4 KPI Cards: Saldo total, Cartera vigente, Cartera vencida, Clientes en mora
- Grafico de linea: Evolucion mensual por tipo de cartera
- Grafico de barras apiladas: Top 10 entidades vigente vs vencida
- Treemap: Participacion por entidad

**Página 2 — Análisis de Mora**
- Gráfico de barras: Tasa de mora por entidad
- Gráfico de línea: Evolución mensual de clientes en mora por tipo de cartera
- Gráfico de dispersión: Relación entre saldo total y cartera vencida por entidad
- Tabla detallada: Top entidades con mayor mora, clientes afectados y tasa de mora

Filtros interactivos: Periodo, Tipo de cartera, Entidad, Producto

---

## Problema resuelto — UnicodeDecodeError byte 0xab

psycopg2 es incompatible con Python 3.14. Al conectarse lee archivos internos del sistema con encoding cp1252 de Windows e intenta interpretarlos como UTF-8, produciendo el error en posicion 96 siempre fija.

Solucion: Migrar a psycopg3:
```bash
pip install psycopg[binary]
```
```python
import psycopg as psycopg2
```

