import io
import re
import zipfile

MAX_BYTES = 50 * 1024 * 1024  # 50 MB de seguridad


def _extraer_texto_gcode(uploaded_file):
    data = uploaded_file.read()
    if len(data) > MAX_BYTES:
        raise ValueError("El archivo es demasiado grande (>50 MB).")

    if data[:2] == b"PK":  # .gcode.3mf es un zip
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            candidatos = [n for n in z.namelist() if n.lower().endswith(".gcode")]
            if not candidatos:
                raise ValueError(
                    "El .3mf no contiene un G-code adentro. "
                    "Vuelve a exportar con 'File > Export > Export plate sliced file'."
                )
            with z.open(candidatos[0]) as f:
                raw = f.read()
    else:
        raw = data

    return raw.decode("utf-8", errors="ignore")


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


def parse_bambu_file(uploaded_file):
    """Extrae tiempo total y peso de filamento de un .gcode o .gcode.3mf de Bambu Studio.

    Es un parser best-effort basado en los comentarios que Bambu Studio agrega
    al encabezado del G-code; el formato puede variar entre versiones, así que
    puede no encontrar todos los datos.
    """
    texto = _extraer_texto_gcode(uploaded_file)
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
