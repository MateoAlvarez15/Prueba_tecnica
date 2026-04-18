# 📊 Distribución de Cartera Financiera — Prueba Técnica

Solución completa para extraer, almacenar y exponer los datos de distribución de cartera
de las entidades financieras colombianas publicados en [datos.gov.co](https://www.datos.gov.co/Hacienda-y-Cr-dito-P-blico/Distribuci-n-de-cartera-por-producto/rvii-eis8/about_data).

---

## 🏗️ Arquitectura

```
datos.gov.co (API Socrata)
        │
        ▼
  rpa/extractor.py  ──►  PostgreSQL (cartera)
                                │
                                ▼
                         api/main.py (FastAPI)
                                │
                                ▼
                         Power BI Dashboard
```

---

## 📁 Estructura del proyecto

```
cartera_rpa/
├── rpa/
│   ├── extractor.py        # RPA: descarga y carga los datos
│   └── requirements.txt
├── api/
│   ├── main.py             # API REST con FastAPI
│   └── requirements.txt
├── db/
│   └── schema.sql          # Definición de tabla e índices
├── .env.example            # Plantilla de variables de entorno
└── README.md
```

---

## ⚙️ Configuración

### 1. Variables de entorno

```bash
cp .env.example .env
# Edita .env con tu cadena de conexión a PostgreSQL
```

```env
DATABASE_URL=postgresql://usuario:contraseña@host:5432/nombre_db
```

### 2. Crear la base de datos

```bash
psql $DATABASE_URL -f db/schema.sql
```

---

## 🤖 RPA — Extracción de datos

```bash
cd rpa
pip install -r requirements.txt
python extractor.py
```

El script:
- Pagina la API Socrata en bloques de 50.000 registros
- Convierte tipos de datos de forma segura
- Inserta en PostgreSQL con `ON CONFLICT DO NOTHING`
- Genera log en `rpa_extractor.log`

---

## 🚀 API — Endpoints disponibles

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

Documentación interactiva: `http://localhost:8000/docs`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Estado de la API |
| GET | `/cartera` | Consulta por entidad y tipo de cartera |
| GET | `/entidades` | Catálogo de entidades |
| GET | `/tipos-cartera` | Catálogo de tipos de cartera |
| GET | `/resumen` | Agregados por tipo de cartera |

### Ejemplo de uso

```bash
# Cartera de Bancolombia tipo libranza
curl "https://tu-api.onrender.com/cartera?entidad=Bancolombia&tipo_cartera=LIBRANZA"

# Resumen general por tipo de cartera
curl "https://tu-api.onrender.com/resumen"

# Catálogo de entidades
curl "https://tu-api.onrender.com/entidades"
```

---

## ☁️ Despliegue (Render.com — gratis)

1. Sube el repo a GitHub
2. Crea un nuevo **Web Service** en [render.com](https://render.com)
3. Configura:
   - **Root directory:** `api`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Agrega la variable de entorno `DATABASE_URL`
5. Deploy ✅

---

## 📊 Power BI

Conecta directamente al PostgreSQL o importa un CSV exportado desde Python.

**Visualizaciones incluidas:**
- Tendencia de saldo total por periodo y tipo de cartera
- Composición de cartera vigente vs vencida
- Ranking de entidades por saldo
- KPIs: saldo total, variación mensual, tasa de mora

**Filtros:** Periodo, Entidad, Tipo de Cartera, Producto

---

## 📋 Criterios cumplidos

- [x] RPA en Python con paginación y logging
- [x] Almacenamiento en PostgreSQL con índices
- [x] API REST funcional con filtros por entidad y tipo de cartera
- [x] Documentación del código (docstrings + README)
- [x] Buenas prácticas: separación por capas, manejo de errores, variables de entorno
