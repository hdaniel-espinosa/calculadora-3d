# Cotizador de Impresión 3D

Calculadora web para generar cotizaciones de impresión 3D (pensada para una Bambu Lab A1), basada en la misma lógica de costeo de la hoja de cálculo `Cotizador_Impresion_3D_Bambu_A1.xlsx`.

No requiere backend ni build: es HTML/CSS/JS puro que corre en el navegador. La configuración de costos y el historial de cotizaciones se guardan en `localStorage` (en el propio navegador del usuario).

## Uso local

Abre `index.html` directamente en el navegador, o sirve la carpeta con cualquier servidor estático, por ejemplo:

```bash
python -m http.server 8000
```

y visita `http://localhost:8000`.

## Cómo calcula el precio

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

Todos estos parámetros (precios de material, electricidad, mano de obra, margen, comisión, tasa de fallos, redondeo) se ajustan desde el botón **⚙ Configuración**, sin tocar el código.

## Publicar el sitio en internet (GitHub Pages, gratis)

1. Crea un repositorio nuevo en GitHub (por ejemplo `cotizador-3d-web`).
2. Sube este proyecto:
   ```bash
   git remote add origin https://github.com/<tu-usuario>/cotizador-3d-web.git
   git branch -M main
   git push -u origin main
   ```
3. En GitHub, ve a **Settings → Pages**, selecciona la rama `main` y la carpeta `/ (root)`.
4. En un par de minutos el sitio queda disponible en `https://<tu-usuario>.github.io/cotizador-3d-web/`.

Alternativa igual de sencilla: arrastrar la carpeta a [Netlify Drop](https://app.netlify.com/drop) para publicarla sin usar git.

## Estructura

```
index.html   estructura de la página (formulario, resultados, modales)
style.css    estilos
app.js       lógica de cálculo, configuración e historial
```

## Notas

- El historial y la configuración viven en el navegador de cada persona (localStorage). Si se abre el sitio desde otro dispositivo o navegador, empieza vacío.
- No hay servidor ni base de datos: es ideal para uso personal o de un solo negocio, no para múltiples usuarios compartiendo datos en tiempo real.
