import math
from datetime import date

import pandas as pd
import streamlit as st

import db
from bambu_parser import parse_bambu_file
from pdf_generator import build_quote_pdf

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

st.session_state.setdefault("peso_pieza_input", 0.0)
st.session_state.setdefault("purga_ams_input", 0.0)
st.session_state.setdefault("horas_impresion", 0)
st.session_state.setdefault("minutos_impresion", 0)
st.session_state.setdefault("horas_postproceso", 0)
st.session_state.setdefault("minutos_postproceso", 0)

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

    with st.expander("📄 Cargar archivo laminado de Bambu Studio (opcional)"):
        st.caption(
            "Sube el .gcode o .gcode.3mf que exporta Bambu Studio al laminar, para prellenar peso y "
            "tiempo automáticamente. Es opcional — solo ahorra escribir los números a mano; siempre "
            "puedes revisarlos y ajustarlos después."
        )
        archivo_laminado = st.file_uploader(
            "Archivo laminado", type=["gcode", "3mf"], label_visibility="collapsed"
        )
        if archivo_laminado is not None:
            try:
                placas = parse_bambu_file(archivo_laminado)
                error_archivo = None
            except Exception as e:
                placas = []
                error_archivo = str(e)

            if error_archivo:
                st.warning(f"No se pudo leer el archivo: {error_archivo}")
            elif not placas:
                st.warning(
                    "No se reconocieron datos en este archivo (puede variar por versión de Bambu "
                    "Studio). Llena los campos manualmente."
                )
            else:
                def _etiqueta_placa(p, i):
                    h = int(p.get("horas", 0))
                    m = round((p.get("horas", 0) - h) * 60)
                    return f"Placa {p.get('index', i + 1)} — {p.get('peso_total_g', 0):.2f} g, {h}h {m}min"

                if len(placas) > 1:
                    st.caption(f"Este archivo tiene {len(placas)} placas de impresión.")
                    opciones = {_etiqueta_placa(p, i): i for i, p in enumerate(placas)}
                    etiqueta_elegida = st.radio(
                        "Elige qué placa cargar", list(opciones.keys()), key="placa_elegida"
                    )
                    plate_idx = opciones[etiqueta_elegida]
                else:
                    plate_idx = 0

                datos_detectados = placas[plate_idx]
                base_huella = getattr(archivo_laminado, "file_id", None) or f"{archivo_laminado.name}:{archivo_laminado.size}"
                huella = f"{base_huella}:{plate_idx}"

                if st.session_state.get("_archivo_procesado") != huella:
                    resumen = []
                    if "peso_total_g" in datos_detectados:
                        st.session_state["peso_pieza_input"] = round(datos_detectados["peso_total_g"], 2)
                        resumen.append(f"peso total: {datos_detectados['peso_total_g']:.2f} g")
                    if "horas" in datos_detectados:
                        h = int(datos_detectados["horas"])
                        m = round((datos_detectados["horas"] - h) * 60)
                        st.session_state["horas_impresion"] = h
                        st.session_state["minutos_impresion"] = m
                        etiqueta = "tiempo total" if datos_detectados.get("tiempo_es_total") else "tiempo de impresión"
                        resumen.append(f"{etiqueta}: {h}h {m}min")
                    if "purga_g" in datos_detectados:
                        st.session_state["purga_ams_input"] = round(datos_detectados["purga_g"], 2)
                        resumen.append(f"purga detectada: {datos_detectados['purga_g']:.2f} g")
                    st.session_state["_archivo_resumen"] = " · ".join(resumen)
                    st.session_state["_archivo_procesado"] = huella
                    st.rerun()

                st.success("Datos aplicados al formulario — " + st.session_state.get("_archivo_resumen", ""))

    c1, c2 = st.columns(2)
    with c1:
        peso_pieza = st.number_input("Peso pieza (g)", min_value=0.0, step=1.0, key="peso_pieza_input")
    with c2:
        purga_ams = st.number_input(
            "Purga AMS (g)",
            min_value=0.0,
            step=1.0,
            key="purga_ams_input",
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
        horas_impresion = st.number_input("Horas", min_value=0, step=1, key="horas_impresion")
    with c2:
        minutos_impresion = st.number_input("Minutos", min_value=0, max_value=59, step=1, key="minutos_impresion")
    horas = horas_impresion + minutos_impresion / 60

    st.caption("Tiempo de postprocesado")
    c1, c2 = st.columns(2)
    with c1:
        horas_postproceso = st.number_input("Horas", min_value=0, step=1, key="horas_postproceso")
    with c2:
        minutos_postproceso = st.number_input("Minutos", min_value=0, max_value=59, step=1, key="minutos_postproceso")
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

    b1, b2, b3 = st.columns(3)
    with b1:
        st.download_button("Descargar cotización (.txt)", quote_text, file_name="cotizacion.txt")
    with b2:
        pdf_bytes = build_quote_pdf(inp, r)
        st.download_button(
            "📄 Descargar PDF",
            pdf_bytes,
            file_name=f"cotizacion_{(nombre_modelo or 'pieza').strip().replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
    with b3:
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
    hist_df_raw = pd.DataFrame(historial)
    hist_df = hist_df_raw.drop(columns=["id"]).copy()
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
    st.caption("Selecciona una fila para poder borrarla individualmente.")
    seleccion = st.dataframe(
        hist_df,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="historial_tabla",
    )
    filas_elegidas = seleccion.selection.rows if seleccion and seleccion.selection else []

    b1, b2 = st.columns(2)
    with b1:
        st.download_button(
            "Exportar historial (CSV)",
            hist_df.to_csv(index=False).encode("utf-8"),
            file_name="historial_cotizaciones.csv",
        )
    with b2:
        if filas_elegidas:
            fila = hist_df_raw.iloc[filas_elegidas[0]]
            if st.button(f"🗑 Borrar cotización seleccionada ({fila['modelo']})"):
                db.delete_cotizacion(int(fila["id"]))
                st.rerun()

    st.divider()
    confirmar_borrado = st.checkbox("Confirmo que quiero borrar todo el historial de forma permanente")
    if st.button("Borrar todo el historial", disabled=not confirmar_borrado):
        db.clear_historial()
        st.rerun()
else:
    st.caption("Sin cotizaciones guardadas todavía.")
