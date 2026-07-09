# Cotizador de Impresión 3D

App en [Streamlit](https://streamlit.io) para generar cotizaciones de impresión 3D (pensada para una Bambu Lab A1). La configuración de costos y el historial de cotizaciones se guardan en una **base de datos Postgres** (recomendado: [Supabase](https://supabase.com), plan gratuito).

**App en vivo:** https://calculadora-3d-impresion.streamlit.app/
**Repositorio:** https://github.com/hdaniel-espinosa/calculadora-3d

## Cómo calcula el precio

1. **Costo material unitario** = (peso pieza + purga AMS) × precio del rollo ÷ peso del rollo
2. **Electricidad unitaria** = horas de impresión × consumo (kW) × costo por kWh
3. **Desgaste unitario** = horas de impresión × desgaste por hora
4. **Mano de obra unitaria** = (minutos de postproceso ÷ 60) × costo de mano de obra por hora
5. **Ajuste por tasa de fallos** = (material + electricidad + desgaste + mano de obra) × % de fallos
6. **Costo total unitario** = subtotal + ajuste por fallos + empaque
7. **Precio sugerido** = costo total × (1 + margen de ganancia)
8. **Precio Mercado Libre** = precio sugerido ÷ (1 − comisión de Mercado Libre)
9. **Precio final** = el anterior según la plataforma elegida, redondeado hacia arriba al múltiplo configurado (por defecto $10)
10. Los totales del pedido multiplican por la **cantidad**.

Todos estos parámetros se ajustan desde el panel **⚙ Configuración de costos** dentro de la app, y quedan guardados en la base de datos para la próxima vez que la abras (o para cualquier otra persona que la use).

## Estructura

```
streamlit_app.py           interfaz y lógica de cálculo
db.py                       esquema y acceso a la base de datos (SQLAlchemy)
requirements.txt            dependencias
.streamlit/secrets.toml.example   formato del secreto de conexión a la base de datos
```

## Base de datos

Se usan tres tablas, creadas automáticamente por la app la primera vez que corre (`db.get_connection()` llama a `metadata.create_all`, no hay que ejecutar SQL a mano):

- `configuracion` — una sola fila con los parámetros generales (peso de rollo, costo eléctrico, mano de obra, margen, comisión, tasa de fallos, redondeo, etc.)
- `materiales` — nombre y precio por rollo de cada material.
- `cotizaciones` — historial de cotizaciones guardadas (fecha, modelo, material, cliente, cantidad, costo, venta, ganancia).

### Configurar la base de datos (Supabase, gratis)

1. Crea una cuenta/proyecto en https://supabase.com (puedes entrar con tu cuenta de GitHub).
2. En el proyecto: **Project Settings → Database → Connection string → URI** — copia la cadena de conexión (modo "Session pooler" recomendado para apps serverless).
3. En Streamlit Cloud: tu app → **⋮ → Settings → Secrets**, y pega:
   ```toml
   [connections.db]
   url = "postgresql://postgres:<tu-password>@<host>:5432/postgres"
   ```
4. Guarda. La app se reinicia sola y crea las tablas automáticamente en el primer request.

Para correr localmente, copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y complétalo con tus datos (ese archivo está en `.gitignore`, nunca se sube al repositorio).

## Uso local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Despliegue

La app ya está conectada a Streamlit Community Cloud: cada `git push` a `main` la vuelve a desplegar automáticamente en 1-2 minutos. Si la app no se usa por un tiempo, Streamlit la "duerme"; el primer visitante después de eso espera unos segundos mientras despierta — es normal.

## Notas

- El plan gratuito de Supabase pausa el proyecto tras ~1 semana sin actividad; basta con abrir el dashboard de Supabase para reactivarlo si eso llega a pasar.
- Todas las personas que usan la app comparten la misma configuración e historial (no hay usuarios ni sesiones separadas). Si necesitas historiales por persona o por negocio, habría que agregar autenticación — no incluido en esta versión.
