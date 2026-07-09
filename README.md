# Cotizador de Impresión 3D

Calculadora para generar cotizaciones de impresión 3D (pensada para una Bambu Lab A1), basada en la misma lógica de costeo de la hoja de cálculo `Cotizador_Impresion_3D_Bambu_A1.xlsx`.

Este repositorio incluye **dos versiones equivalentes**, mismos cálculos, dos formas de publicarla:

| Versión | Archivos | Dónde se despliega |
|---|---|---|
| Sitio estático (HTML/CSS/JS) | `index.html`, `style.css`, `app.js` | GitHub Pages / Netlify |
| App Python | `streamlit_app.py`, `requirements.txt` | [Streamlit Community Cloud](https://streamlit.io) |

Repositorio: https://github.com/hdaniel-espinosa/calculadora-3d

## Cómo calcula el precio (ambas versiones)

1. **Costo material unitario** = (peso pieza + purga AMS) × precio del rollo ÷ peso del rollo
2. **Electricidad unitaria** = horas de impresión × consumo (kW) × costo por kWh
3. **Desgaste unitario** = horas de impresión × desgaste por hora
4. **Mano de obra unitaria** = (minutos de postproceso ÷ 60) × costo de mano de obra por hora
5. **Ajuste por tasa de fallos** = (material + electricidad + desgaste + mano de obra) × % de fallos
6. **Costo total unitario** = subtotal + ajuste por fallos + empaque
7. **Precio sugerido** = costo total × (1 + margen de ganancia)
8. **Precio Mercado Libre** = precio sugerido ÷ (1 − comisión de Mercado Libre)
9. **Precio final** = el anterior, según la plataforma elegida, redondeado hacia arriba al múltiplo configurado (por defecto $10)
10. Los totales del pedido multiplican por la **cantidad**.

Todos estos parámetros (precios de material, electricidad, mano de obra, margen, comisión, tasa de fallos, redondeo) se ajustan desde el panel de Configuración, sin tocar el código.

## Versión estática (HTML/CSS/JS)

No requiere backend ni build. La configuración y el historial se guardan en `localStorage` del navegador.

Uso local:
```bash
python -m http.server 8000
```
y visita `http://localhost:8000`.

### Publicar en GitHub Pages
En GitHub → **Settings → Pages** → rama `main` → carpeta `/ (root)`. Queda disponible en `https://hdaniel-espinosa.github.io/calculadora-3d/`.

Alternativa: arrastrar la carpeta a [Netlify Drop](https://app.netlify.com/drop).

## Versión Streamlit (Python)

Misma lógica de cálculo, reescrita en `streamlit_app.py`. La configuración y el historial viven en la sesión del navegador (`st.session_state`) — se reinician si recargas la página o si la app se "duerme" por inactividad.

Uso local:
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Publicar en Streamlit Community Cloud
1. Entra a **https://share.streamlit.io** e inicia sesión con tu cuenta de GitHub (la misma dueña de este repo).
2. Clic en **"New app"** (o **"Create app"**).
3. Selecciona el repositorio `hdaniel-espinosa/calculadora-3d`, rama `main`, archivo principal `streamlit_app.py`.
4. Clic en **Deploy**. En 1-2 minutos queda publicada en una URL tipo `https://calculadora-3d-<algo>.streamlit.app`.

Este último paso requiere iniciar sesión con tu cuenta, así que no se puede automatizar de este lado — el resto del trabajo (código, repo, requirements.txt) ya está listo para que solo falten esos clics.

## Estructura

```
index.html         sitio estático: estructura de la página
style.css           sitio estático: estilos
app.js              sitio estático: lógica de cálculo, configuración e historial
streamlit_app.py    app Streamlit equivalente en Python
requirements.txt    dependencias de la app Streamlit
```

## Excel

`excel/Cotizador_Impresion_3D_Bambu_A1_v2.xlsx` es la versión mejorada de la hoja de cálculo original: agrega totales por cantidad, selección de plataforma funcional, tabla de materiales ampliable, tasa de fallos, redondeo de precio y formato profesional.

## Notas

- Las dos versiones implementan la misma fórmula por separado (una en JavaScript, otra en Python). Si cambias la lógica de costeo, actualiza ambas.
- Ninguna de las dos versiones tiene base de datos: el historial vive solo en el navegador/sesión de quien la usa, no se comparte entre dispositivos ni usuarios.
