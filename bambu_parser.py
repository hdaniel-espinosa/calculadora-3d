import re
import xml.etree.ElementTree as ET
import zipfile

# Tope de seguridad para el tamaño total del archivo (no se lee completo en
# memoria salvo que sea necesario -- ver parse_bambu_file).
MAX_BYTES = 500 * 1024 * 1024

# El encabezado con los datos que buscamos siempre está al inicio del .gcode,
# así que basta con leer un prefijo aunque el archivo pese cientos de MB.
HEADER_PREFIX_BYTES = 512 * 1024


def _tiempo_a_horas(fragmento):
    horas = re.search(r"(\d+)\s*h", fragmento)
    minutos = re.search(r"(\d+)\s*m(?!s)", fragmento)
    segundos = re.search(r"(\d+)\s*s", fragmento)
    total_min = 0.0
    if horas:
        total_min += int(horas.group(1)) * 60
    if minutos:
        total_min += int(minutos.group(1))
    if segundos:
        total_min += int(segundos.group(1)) / 60
    return total_min / 60 if total_min else None


def _parse_gcode_text(texto):
    """Parser best-effort de los comentarios de encabezado de un .gcode.

    El formato puede variar entre versiones de Bambu Studio.
    """
    resultado = {}

    tiempo_total = re.search(r"total estimated time[^\n;]*?:\s*([\dhms\s]{1,20})", texto, re.IGNORECASE)
    tiempo_modelo = re.search(r"model printing time[^\n;]*?:\s*([\dhms\s]{1,20})", texto, re.IGNORECASE)
    match_tiempo = tiempo_total or tiempo_modelo
    if match_tiempo:
        horas = _tiempo_a_horas(match_tiempo.group(1))
        if horas is not None:
            resultado["horas"] = horas
            resultado["tiempo_es_total"] = bool(tiempo_total)

    peso = re.search(r"total filament weight\s*\[g\]\s*:?\s*([\d.]+)", texto, re.IGNORECASE)
    if not peso:
        peso = re.search(r"filament weight\s*\[g\]\s*:?\s*([\d.]+)", texto, re.IGNORECASE)
    if peso:
        resultado["peso_total_g"] = float(peso.group(1))

    purga = re.search(r"(?:flush|purge|wipe tower)[^\n;]*?weight\s*\[g\]\s*:?\s*([\d.]+)", texto, re.IGNORECASE)
    if purga:
        resultado["purga_g"] = float(purga.group(1))

    return resultado


def _parse_slice_info(data):
    """Parser del XML Metadata/slice_info.config: una placa por <plate>, con
    peso e índice reales, más confiable que leer texto del gcode."""
    root = ET.fromstring(data)
    placas = []
    for plate in root.findall("plate"):
        meta = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
        item = {}
        index = meta.get("index")
        if index:
            item["index"] = int(index)
        peso = meta.get("weight")
        if peso:
            item["peso_total_g"] = float(peso)
        prediccion = meta.get("prediction")  # segundos
        if prediccion:
            item["horas"] = float(prediccion) / 3600
            item["tiempo_es_total"] = True
        if "peso_total_g" in item or "horas" in item:
            placas.append(item)
    return placas


def parse_bambu_file(uploaded_file):
    """Extrae tiempo total y peso de filamento de un .gcode o .gcode.3mf de
    Bambu Studio. Devuelve una lista de placas (una por cada plato del
    proyecto); un .gcode plano siempre devuelve una sola.

    No lee el archivo completo en memoria: para un .gcode plano basta con
    el encabezado (los datos que buscamos están en las primeras líneas), y
    para un .3mf se usa el archivo tal cual (zipfile solo lee lo necesario).
    """
    tamano = getattr(uploaded_file, "size", None)
    if tamano is not None and tamano > MAX_BYTES:
        raise ValueError(
            f"El archivo pesa {tamano / 1024 / 1024:.0f} MB, más que el límite de "
            f"{MAX_BYTES // 1024 // 1024} MB."
        )

    cabecera = uploaded_file.read(2)
    uploaded_file.seek(0)

    if cabecera != b"PK":
        # .gcode plano: solo se lee el prefijo con el encabezado.
        texto = uploaded_file.read(HEADER_PREFIX_BYTES).decode("utf-8", errors="ignore")
        item = _parse_gcode_text(texto)
        return [item] if item else []

    with zipfile.ZipFile(uploaded_file) as z:
        nombres = z.namelist()

        if "Metadata/slice_info.config" in nombres:
            placas = _parse_slice_info(z.read("Metadata/slice_info.config"))
            if placas:
                return placas

        # Respaldo: no hay slice_info.config o no trajo datos utilizables,
        # parsear el encabezado de cada plate_N.gcode encontrado dentro del zip.
        gcode_nombres = sorted(n for n in nombres if n.lower().endswith(".gcode"))
        if not gcode_nombres:
            raise ValueError(
                "El .3mf no contiene un G-code adentro. "
                "Vuelve a exportar con 'File > Export > Export plate sliced file'."
            )
        placas = []
        for i, nombre in enumerate(gcode_nombres):
            with z.open(nombre) as f:
                texto = f.read(HEADER_PREFIX_BYTES).decode("utf-8", errors="ignore")
            item = _parse_gcode_text(texto)
            if item:
                match = re.search(r"plate_(\d+)", nombre)
                item["index"] = int(match.group(1)) if match else i + 1
                placas.append(item)
        return placas
