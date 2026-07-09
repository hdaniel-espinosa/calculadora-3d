import math
from datetime import date

import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Cotizador de Impresión 3D", page_icon="🖨️", layout="wide")

try:
    db.get_connection()
except Exception as e:
    st.error(
        "**No se pudo conectar a la base de datos.**\n\n"
        "Configura el secreto de conexión en Streamlit Cloud "
        "(⋮ → Settings → Secrets) con el siguiente formato:\n\n"
        '```toml\n[connections.db]\nurl = "postgresql://usuario:password@host:5432/postgres"\n```\n\n'
        "Usa la cadena de conexión de tu proyecto de Supabase "
        "(Project Settings → Database → Connection string → URI)."
    )
    st.caption(f"Detalle técnico: {e}")
    st.stop()


def ceil_to_multiple(value, multiple):
    if not multiple or multiple <= 0:
        return value
    return math.ceil(value / multiple) * multiple


def calcular(inp, cfg, materiales):
    precios = {m["nombre"]: float(m["precio_rollo"]) for m in materiales}
    precio_rollo = precios.get(inp["material"], 0.0)

    peso_rollo = float(cfg["peso_rollo"]) or 1.0
    costo_material = (inp["peso_pieza"] + inp["purga_ams"]) * precio_rollo / peso_rollo
    electricidad = inp["horas"] * float(cfg["consumo_a1"]) * float(cfg["costo_electricidad"])
    desgaste = inp["horas"] * float(cfg["desgaste_por_hora"])
    mano_obra = (inp["min_postproceso"] / 60) * float(cfg["mano_obra_por_hora"])

    subtotal = costo_material + electricidad + desgaste + mano_obra
    ajuste_fallos = subtotal * (float(cfg["tasa_fallos"]) / 100)
    empaque = float(cfg["empaque_basico"])
    costo_total_unitario = subtotal + ajuste_fallos + empaque

    precio_sugerido = costo_total_unitario * (1 + float(cfg["margen_ganancia"]) / 100)
    denom = 1 - float(cfg["comision_ml"]) / 100
    precio_ml = precio_sugerido / denom if denom else precio_sugerido
    precio_final_unitario = precio_ml if inp["plataforma"] == "Mercado Libre" else precio_sugerido
    precio_redondeado = ceil_to_multiple(precio_final_unitario, float(cfg["redondeo"]))
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


cfg = db.load_config()
materiales = db.load_materiales()

st.title("🖨️ Cotizador de Impresión 3D")
st.caption("Bambu Lab A1 — cotizaciones y configuración guardadas en base de datos")

with st.expander("⚙ Configuración de costos"):
    st.markdown("**Materiales (precio por rollo de 1 kg)**")
    materiales_df = pd.DataFrame(materiales, columns=["nombre", "precio_rollo"])
    edited = st.data_editor(
        materiales_df,
        num_rows="dynamic",
        use_container_width=True,
        key="materiales_editor",
        column_config={
            "nombre": st.column_config.TextColumn("Material", required=True),
            "precio_rollo": st.column_config.NumberColumn("Precio rollo ($)", min_value=0.0, format="$%.2f", required=True),
        },
    )

    c1, c2 = st.columns(2)
    with c1:
        peso_rollo = st.number_input("Peso del rollo (g)", min_value=1.0, value=float(cfg["peso_rollo"]))
        costo_electricidad = st.number_input("Costo electricidad ($/kWh)", min_value=0.0, value=float(cfg["costo_electricidad"]))
        consumo_a1 = st.number_input("Consumo promedio A1 (kW)", min_value=0.0, value=float(cfg["consumo_a1"]))
        desgaste_por_hora = st.number_input("Desgaste impresora por hora ($)", min_value=0.0, value=float(cfg["desgaste_por_hora"]))
        mano_obra_por_hora = st.number_input("Mano de obra por hora ($)", min_value=0.0, value=float(cfg["mano_obra_por_hora"]))
    with c2:
        empaque_basico = st.number_input("Empaque básico ($)", min_value=0.0, value=float(cfg["empaque_basico"]))
        tasa_fallos = st.number_input("Tasa de fallos / desperdicio (%)", min_value=0.0, value=float(cfg["tasa_fallos"]))
        margen_ganancia = st.number_input("Margen de ganancia (%)", min_value=0.0, value=float(cfg["margen_ganancia"]))
        comision_ml = st.number_input("Comisión Mercado Libre (%)", min_value=0.0, max_value=99.0, value=float(cfg["comision_ml"]))
        redondeo = st.number_input("Redondeo de precio final (múltiplo de $)", min_value=0.0, value=float(cfg["redondeo"]))

    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Guardar configuración", type="primary"):
            db.save_materiales(edited.to_dict("records"))
            db.save_config(
                {
                    "peso_rollo": peso_rollo,
                    "costo_electricidad": costo_electricidad,
                    "consumo_a1": consumo_a1,
                    "desgaste_por_hora": desgaste_por_hora,
                    "mano_obra_por_hora": mano_obra_por_hora,
                    "empaque_basico": empaque_basico,
                    "tasa_fallos": tasa_fallos,
                    "margen_ganancia": margen_ganancia,
                    "comision_ml": comision_ml,
                    "redondeo": redondeo,
                }
            )
            st.success("Configuración guardada en la base de datos.")
            st.rerun()
    with b2:
        if st.button("Restaurar valores por defecto"):
            db.save_config(db.DEFAULT_CONFIG)
            db.save_materiales(db.DEFAULT_MATERIALES)
            st.rerun()

col_form, col_result = st.columns(2)

with col_form:
    st.subheader("Datos de la pieza")
    nombre_modelo = st.text_input("Nombre del modelo", placeholder="Ej. Soporte para celular")
    nombres_materiales = [m["nombre"] for m in materiales] or ["(sin materiales)"]
    material = st.selectbox("Material", nombres_materiales)

    c1, c2 = st.columns(2)
    with c1:
        peso_pieza = st.number_input("Peso pieza (g)", min_value=0.0, value=50.0, step=1.0)
    with c2:
        purga_ams = st.number_input(
            "Purga AMS (g)",
            min_value=0.0,
            value=5.0,
            step=1.0,
            help=(
                "Filamento que se desperdicia cuando el AMS cambia de color o material durante la "
                "impresión (las purgas/torres de purga que limpian la boquilla antes de extruir el "
                "nuevo filamento).\n\n"
                "- Pieza de un solo color/material: deja este campo en 0.\n"
                "- Pieza multicolor con AMS: en Bambu Studio, después de laminar, compara el peso "
                "total de filamento del proyecto contra el peso del modelo + soportes — la diferencia "
                "es lo que se purgó. Si no tienes el dato exacto, una referencia común es 2-5 g por "
                "cada cambio de color."
            ),
        )

    st.caption("Tiempo de impresión")
    c1, c2 = st.columns(2)
    with c1:
        horas_impresion = st.number_input("Horas", min_value=0, value=0, step=1, key="horas_impresion")
    with c2:
        minutos_impresion = st.number_input("Minutos", min_value=0, max_value=59, value=31, step=1, key="minutos_impresion")
    horas = horas_impresion + minutos_impresion / 60

    st.caption("Tiempo de postprocesado")
    c1, c2 = st.columns(2)
    with c1:
        horas_postproceso = st.number_input("Horas", min_value=0, value=0, step=1, key="horas_postproceso")
    with c2:
        minutos_postproceso = st.number_input("Minutos", min_value=0, max_value=59, value=10, step=1, key="minutos_postproceso")
    min_postproceso = horas_postproceso * 60 + minutos_postproceso

    c1, c2 = st.columns(2)
    with c1:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
    with c2:
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
r = calcular(inp, cfg, materiales)

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
        if st.button("Guardar en historial", type="primary"):
            db.save_cotizacion(
                {
                    "modelo": nombre_modelo or "(sin nombre)",
                    "material": material,
                    "cliente": cliente or None,
                    "cantidad": int(cantidad),
                    "costo_total": round(r["costo_total_pedido"], 2),
                    "precio_total": round(r["precio_total_pedido"], 2),
                    "ganancia_total": round(r["ganancia_total_pedido"], 2),
                }
            )
            st.success("Cotización guardada en la base de datos.")
            st.rerun()

st.divider()
st.subheader("📋 Historial de cotizaciones")
historial = db.load_historial()
if historial:
    hist_df = pd.DataFrame(historial).drop(columns=["id"])
    hist_df["fecha"] = pd.to_datetime(hist_df["fecha"]).dt.strftime("%d/%m/%Y %H:%M")
    hist_df["cliente"] = hist_df["cliente"].fillna("-")
    for col in ["costo_total", "precio_total", "ganancia_total"]:
        hist_df[col] = hist_df[col].astype(float).map(money)
    hist_df = hist_df.rename(
        columns={
            "fecha": "Fecha",
            "modelo": "Modelo",
            "material": "Material",
            "cliente": "Cliente",
            "cantidad": "Cantidad",
            "costo_total": "Costo",
            "precio_total": "Venta",
            "ganancia_total": "Ganancia",
        }
    )
    st.dataframe(hist_df, hide_index=True, use_container_width=True)
    st.download_button(
        "Exportar historial (CSV)",
        hist_df.to_csv(index=False).encode("utf-8"),
        file_name="historial_cotizaciones.csv",
    )

    confirmar_borrado = st.checkbox("Confirmo que quiero borrar todo el historial de forma permanente")
    if st.button("Borrar historial", disabled=not confirmar_borrado):
        db.clear_historial()
        st.rerun()
else:
    st.caption("Sin cotizaciones guardadas todavía.")
