from datetime import date

from fpdf import FPDF


def _money(v):
    return f"${v:,.2f}"


def build_quote_pdf(inp, r):
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Cotizacion de Impresion 3D", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 7, f"Fecha: {date.today().strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    if inp.get("cliente"):
        pdf.cell(0, 7, f"Cliente: {inp['cliente']}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Detalle de la pieza", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    filas = [
        ("Modelo", inp.get("nombre_modelo") or "(sin nombre)"),
        ("Material", inp.get("material", "")),
        ("Cantidad", str(inp.get("cantidad", ""))),
        ("Plataforma", inp.get("plataforma", "")),
    ]
    for etiqueta, valor in filas:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 8, etiqueta + ":")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, str(valor), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(90, 10, "Precio unitario:")
    pdf.cell(0, 10, _money(r["precio_redondeado"]), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(90, 10, "Precio total:")
    pdf.cell(0, 10, _money(r["precio_total_pedido"]), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, "Gracias por tu preferencia!", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
