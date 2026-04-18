-- ============================================================
-- Schema: Distribución de Cartera por Producto
-- Fuente: datos.gov.co | Dataset: rvii-eis8
-- ============================================================

CREATE TABLE IF NOT EXISTS cartera (
    id                  SERIAL PRIMARY KEY,

    -- Identificación de entidad
    tipo_entidad        INTEGER,
    codigo_entidad      INTEGER,
    nombreentidad       VARCHAR(255),

    -- Periodo y producto
    fecha_corte         TIMESTAMP,
    unicap              INTEGER,
    descrip_uc          VARCHAR(255),   -- Tipo/descripción de cartera (ej: LIBRE INVERSIÓN)
    renglon             INTEGER,
    desc_renglon        VARCHAR(255),   -- Producto específico

    -- Saldos (en pesos colombianos)
    saldo_total         NUMERIC(25, 2),
    vigente             NUMERIC(25, 2),

    -- Cartera vencida (distintos rangos según tipo de entidad)
    vencida_1_2_meses   NUMERIC(25, 2),
    vencida_2_3_meses   NUMERIC(25, 2),
    vencida_1_3_meses   NUMERIC(25, 2),
    vencida_3_4_meses   NUMERIC(25, 2),
    vencida_4_meses     NUMERIC(25, 2),
    vencida_3_6_meses   NUMERIC(25, 2),
    vencida_6_meses     NUMERIC(25, 2),
    vencida_1_4_meses   NUMERIC(25, 2),
    vencida_4_6_meses   NUMERIC(25, 2),
    vencida_6_12_meses  NUMERIC(25, 2),
    vencida_12_18_meses NUMERIC(25, 2),
    vencida_12_meses    NUMERIC(25, 2),
    vencida_18_meses    NUMERIC(25, 2),

    -- Clientes en mora
    num_clientes_mora   INTEGER,

    -- Auditoría
    created_at          TIMESTAMP DEFAULT NOW()
);

-- ──────────────────────────────────────────────
-- Índices para mejorar rendimiento de la API
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cartera_entidad
    ON cartera(nombreentidad);

CREATE INDEX IF NOT EXISTS idx_cartera_tipo
    ON cartera(descrip_uc);

CREATE INDEX IF NOT EXISTS idx_cartera_fecha
    ON cartera(fecha_corte);

CREATE INDEX IF NOT EXISTS idx_cartera_producto
    ON cartera(desc_renglon);

CREATE INDEX IF NOT EXISTS idx_cartera_codigo
    ON cartera(codigo_entidad);
