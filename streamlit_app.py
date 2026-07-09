import math
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cotizador de Impresión 3D", page_icon="🖨️", layout="wide")

DEFAULT_CONFIG = {
    "materiales": [
        {"Material": "PLA Pro", "Precio rollo ($)": 279.0},
        {"Material": "PLA Matte", "Precio rollo ($)": 289.0},
    ],
    "peso_rollo": 1000.0,
    "costo_electricidad": 2.8,
    "consumo_a1": 0.1,
    "desgaste_por_hora": 6.0,
    "mano_obra_por_hora": 180.0,
    "empaque_basico": 8.0,
    "tasa_fallos": 5.0,
    "margen_ganancia": 40.0,
    "comision_ml": 16.0,
    "redondeo": 10.0,
}


def init_state():
    if "config" not in st.session_state:
        st.session_state.config = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_CONFIG.items()}
        st.session_state.config["materiales"] = [dict(m) for m in DEFAULT_CONFIG["materiales"]]
    if "historial" not in st.session_state:
        st.session_state.historial = []


def ceil_to_multiple(value, multiple):
    if not multiple or multiple <= 0:
        return value
    return math.ceil(value / multiple) * multiple


def calcular(inp, cfg):
    materiales = {m["Material"]: m["Precio rollo ($)"] for m in cfg["materiales"] if m["Material"]}
    precio_rollo = materiales.get(inp["material"], 0.0)

    costo_material = (inp["peso_pieza"] + inp["purga_ams"]) * precio_rollo / cfg["peso_rollo"] if cfg["peso_rollo"] else 0
    electricidad = inp["horas"] * cfg["consumo_a1"] * cfg["costo_electricidad"]
    desgaste = inp["horas"] * cfg["desgaste_por_hora"]
    mano_obra = (inp["min_postproceso"] / 60) * cfg["mano_obra_por_hora"]

    subtotal = costo_material + electricidad + desgaste + mano_obra
    ajuste_fallos = subtotal * (cfg["tasa_fallos"] / 100)
    empaque = cfg["empaque_basico"]
    costo_total_unitario = subtotal + ajuste_fallos + empaque

    precio_sugerido = costo_total_unitario * (1 + cfg["margen_ganancia"] / 100)
    denom = 1 - cfg["comision_ml"] / 100
    precio_ml = precio_sugerido / denom if denom else precio_sugerido
    precio_final_unitario = precio_ml if inp["plataforma"] == "Mercado Libre" else precio_sugerido
    precio_redondeado = ceil_to_multiple(precio_final_unitario, cfg["redondeo"])
    ganancia_unitaria = precio_redondeado - costo_total_unitario

    costo_total_pedido = costo_total_unitario * inp["cantidad"]
    precio_total_pedido = precio_redondeado * inp["cantidad"]
    ganancia_total_pedido = precio_total_pedido - costo_total_pedido

    return {
        "precio_rollo": precio_rollo,
        "costo_material": costo_material,
        "electricidad": electricidad,
        "desgaste": desgaste,
        "mano_obra": mano_obra,
        "subtotal": subtotal,
        "ajuste_fallos": ajuste_fallos,
        "empaque": empaque,
        "costo_total_unitario": costo_total_unitario,
        "precio_sugerido": precio_sugerido,
        "precio_ml": precio_ml,
        "precio_final_unitario": precio_final_unitario,
        "precio_redondeado": precio_redondeado,
        "ganancia_unitaria": ganancia_unitaria,
        "costo_total_pedido": costo_total_pedido,
        "precio_total_pedido": precio_total_pedido,
        "ganancia_total_pedido": ganancia_total_pedido,
    }


def money(v):
    return f"${v:,.2f}"


def build_quote_text(inp, r):
    lines = [
        "COTIZACIÓN DE IMPRESIÓN 3D",
        f"Fecha: {date.today().strftime('%d/%m/%Y')}",
    ]
    if inp["cliente"]:
        lines.append(f"Cliente: {inp['cliente']}")
    lines += [
        "",
        f"Modelo: {inp['nombre_modelo'] or '(sin nombre)'}",
        f"Material: {inp['material']}",
        f"Cantidad: {inp['cantidad']}",
        f"Plataforma: {inp['plataforma']}",
        "",
        f"Precio unitario: {money(r['precio_redondeado'])}",
        f"Precio total: {money(r['precio_total_pedido'])}",
        "",
        "¡Gracias por tu preferencia!",
    ]
    return "\n".join(lines)


init_state()
cfg = st.session_state.config

st.title("🖨️ Cotizador de Impresión 3D")
st.caption("Misma lógica de costeo que el Excel y la calculadora web — Bambu Lab A1")

with st.expander("⚙ Configuración de costos"):
    st.markdown("**Materiales (precio por rollo de 1 kg)**")
    materiales_df = pd.DataFrame(cfg["materiales"])
    edited = st.data_editor(
        materiales_df,
        num_rows="dynamic",
        use_container_width=True,
        key="materiales_editor",
        column_config={
            "Material": st.column_config.TextColumn(required=True),
            "Precio rollo ($)": st.column_config.NumberColumn(min_value=0.0, format="$%.2f", required=True),
        },
    )
    cfg["materiales"] = edited.dropna(subset=["Material"]).to_dict("records")

    c1, c2 = st.columns(2)
    with c1:
        cfg["peso_rollo"] = st.number_input("Peso del rollo (g)", min_value=1.0, value=float(cfg["peso_rollo"]))
        cfg["costo_electricidad"] = st.number_input("Costo electricidad ($/kWh)", min_value=0.0, value=float(cfg["costo_electricidad"]))
        cfg["consumo_a1"] = st.number_input("Consumo promedio A1 (kW)", min_value=0.0, value=float(cfg["consumo_a1"]))
        cfg["desgaste_por_hora"] = st.number_input("Desgaste impresora por hora ($)", min_value=0.0, value=float(cfg["desgaste_por_hora"]))
        cfg["mano_obra_por_hora"] = st.number_input("Mano de obra por hora ($)", min_value=0.0, value=float(cfg["mano_obra_por_hora"]))
    with c2:
        cfg["empaque_basico"] = st.number_input("Empaque básico ($)", min_value=0.0, value=float(cfg["empaque_basico"]))
        cfg["tasa_fallos"] = st.number_input("Tasa de fallos / desperdicio (%)", min_value=0.0, value=float(cfg["tasa_fallos"]))
        cfg["margen_ganancia"] = st.number_input("Margen de ganancia (%)", min_value=0.0, value=float(cfg["margen_ganancia"]))
        cfg["comision_ml"] = st.number_input("Comisión Mercado Libre (%)", min_value=0.0, max_value=99.0, value=float(cfg["comision_ml"]))
        cfg["redondeo"] = st.number_input("Redondeo de precio final (múltiplo de $)", min_value=0.0, value=float(cfg["redondeo"]))

    if st.button("Restaurar valores por defecto"):
        st.session_state.config = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_CONFIG.items()}
        st.session_state.config["materiales"] = [dict(m) for m in DEFAULT_CONFIG["materiales"]]
        st.rerun()

col_form, col_result = st.columns(2)

with col_form:
    st.subheader("Datos de la pieza")
    nombre_modelo = st.text_input("Nombre del modelo", placeholder="Ej. Soporte para celular")
    nombres_materiales = [m["Material"] for m in cfg["materiales"] if m["Material"]] or ["(sin materiales)"]
    material = st.selectbox("Material", nombres_materiales)

    c1, c2 = st.columns(2)
    with c1:
        peso_pieza = st.number_input("Peso pieza (g)", min_value=0.0, value=50.0, step=1.0)
        horas = st.number_input("Horas de impresión", min_value=0.0, value=3.0, step=0.1)
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
    with c2:
        purga_ams = st.number_input("Purga AMS (g)", min_value=0.0, value=5.0, step=1.0)
        min_postproceso = st.number_input("Minutos de postproceso", min_value=0.0, value=10.0, step=1.0)
        plataforma = st.selectbox("Plataforma de venta", ["Venta directa", "Mercado Libre"])

    cliente = st.text_input("Cliente (opcional)")

inp = {
    "nombre_modelo": nombre_modelo,
    "material": material,
    "peso_pieza": peso_pieza,
    "purga_ams": purga_ams,
    "horas": horas,
    "min_postproceso": min_postproceso,
    "cantidad": cantidad,
    "plataforma": plataforma,
    "cliente": cliente,
}
r = calcular(inp, cfg)

with col_result:
    st.subheader("Desglose de costos")
    breakdown = pd.DataFrame(
        [
            ["Precio rollo del material", money(r["precio_rollo"])],
            ["Costo material unitario", money(r["costo_material"])],
            ["Electricidad unitaria", money(r["electricidad"])],
            ["Desgaste unitario", money(r["desgaste"])],
            ["Mano de obra unitaria", money(r["mano_obra"])],
            ["Subtotal antes de fallos", money(r["subtotal"])],
            ["Ajuste por tasa de fallos", money(r["ajuste_fallos"])],
            ["Empaque unitario", money(r["empaque"])],
            ["Costo total unitario", money(r["costo_total_unitario"])],
        ],
        columns=["Concepto", "Valor"],
    )
    st.dataframe(breakdown, hide_index=True, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Precio final unitario", money(r["precio_redondeado"]))
    m2.metric("Precio total del pedido", money(r["precio_total_pedido"]))
    m3.metric("Ganancia total estimada", money(r["ganancia_total_pedido"]))

    quote_text = build_quote_text(inp, r)
    st.text_area("Cotización generada", quote_text, height=180)

    b1, b2 = st.columns(2)
    with b1:
        st.download_button("Descargar cotización (.txt)", quote_text, file_name="cotizacion.txt")
    with b2:
        if st.button("Guardar en historial"):
            st.session_state.historial.insert(
                0,
                {
                    "Fecha": date.today().strftime("%d/%m/%Y"),
                    "Modelo": nombre_modelo or "(sin nombre)",
                    "Cliente": cliente or "-",
                    "Cantidad": cantidad,
                    "Costo": round(r["costo_total_pedido"], 2),
                    "Venta": round(r["precio_total_pedido"], 2),
                    "Ganancia": round(r["ganancia_total_pedido"], 2),
                },
            )
            st.success("Cotización guardada en el historial de esta sesión.")

st.divider()
st.subheader("📋 Historial de esta sesión")
if st.session_state.historial:
    hist_df = pd.DataFrame(st.session_state.historial)
    st.dataframe(hist_df, hide_index=True, use_container_width=True)
    st.download_button(
        "Exportar historial (CSV)",
        hist_df.to_csv(index=False).encode("utf-8"),
        file_name="historial_cotizaciones.csv",
    )
    if st.button("Borrar historial"):
        st.session_state.historial = []
        st.rerun()
else:
    st.caption("Sin registros aún. El historial vive solo en esta sesión del navegador.")
