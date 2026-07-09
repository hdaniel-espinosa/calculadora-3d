import streamlit as st
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    delete,
    func,
    insert,
    select,
    update,
)

DEFAULT_CONFIG = {
    "peso_rollo": 1000,
    "costo_electricidad": 2.8,
    "consumo_a1": 0.1,
    "desgaste_por_hora": 6,
    "mano_obra_por_hora": 180,
    "empaque_basico": 8,
    "tasa_fallos": 5,
    "margen_ganancia": 40,
    "comision_ml": 16,
    "redondeo": 10,
}

DEFAULT_MATERIALES = [
    {"nombre": "PLA Pro", "precio_rollo": 279},
    {"nombre": "PLA Matte", "precio_rollo": 289},
]

metadata = MetaData()

materiales_t = Table(
    "materiales",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String, unique=True, nullable=False),
    Column("precio_rollo", Numeric, nullable=False),
)

configuracion_t = Table(
    "configuracion",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("peso_rollo", Numeric, nullable=False),
    Column("costo_electricidad", Numeric, nullable=False),
    Column("consumo_a1", Numeric, nullable=False),
    Column("desgaste_por_hora", Numeric, nullable=False),
    Column("mano_obra_por_hora", Numeric, nullable=False),
    Column("empaque_basico", Numeric, nullable=False),
    Column("tasa_fallos", Numeric, nullable=False),
    Column("margen_ganancia", Numeric, nullable=False),
    Column("comision_ml", Numeric, nullable=False),
    Column("redondeo", Numeric, nullable=False),
)

cotizaciones_t = Table(
    "cotizaciones",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fecha", DateTime, server_default=func.now(), nullable=False),
    Column("modelo", String),
    Column("material", String),
    Column("cliente", String),
    Column("cantidad", Integer, nullable=False),
    Column("costo_total", Numeric, nullable=False),
    Column("precio_total", Numeric, nullable=False),
    Column("ganancia_total", Numeric, nullable=False),
)


@st.cache_resource(show_spinner=False)
def get_connection():
    conn = st.connection("db", type="sql")
    metadata.create_all(conn.engine)
    with conn.session as s:
        if s.execute(select(configuracion_t)).first() is None:
            s.execute(insert(configuracion_t).values(id=1, **DEFAULT_CONFIG))
        if s.execute(select(materiales_t)).first() is None:
            s.execute(insert(materiales_t), DEFAULT_MATERIALES)
        s.commit()
    return conn


def load_config():
    conn = get_connection()
    with conn.session as s:
        row = s.execute(select(configuracion_t).where(configuracion_t.c.id == 1)).mappings().first()
    return dict(row)


def save_config(cfg):
    conn = get_connection()
    campos = {k: cfg[k] for k in DEFAULT_CONFIG}
    with conn.session as s:
        s.execute(update(configuracion_t).where(configuracion_t.c.id == 1).values(**campos))
        s.commit()


def load_materiales():
    conn = get_connection()
    with conn.session as s:
        rows = s.execute(select(materiales_t).order_by(materiales_t.c.id)).mappings().all()
    return [dict(r) for r in rows]


def save_materiales(materiales):
    conn = get_connection()
    limpio = [
        {"nombre": str(m["nombre"]).strip(), "precio_rollo": float(m["precio_rollo"] or 0)}
        for m in materiales
        if str(m.get("nombre") or "").strip()
    ]
    with conn.session as s:
        s.execute(delete(materiales_t))
        if limpio:
            s.execute(insert(materiales_t), limpio)
        s.commit()


def save_cotizacion(record):
    conn = get_connection()
    with conn.session as s:
        s.execute(insert(cotizaciones_t).values(**record))
        s.commit()


def load_historial(limit=200):
    conn = get_connection()
    with conn.session as s:
        rows = (
            s.execute(select(cotizaciones_t).order_by(cotizaciones_t.c.fecha.desc()).limit(limit))
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


def clear_historial():
    conn = get_connection()
    with conn.session as s:
        s.execute(delete(cotizaciones_t))
        s.commit()
