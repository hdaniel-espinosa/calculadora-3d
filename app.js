// ---------- Configuración por defecto (mismos valores que la hoja "Configuracion" del Excel) ----------
const DEFAULT_CONFIG = {
  materiales: [
    { nombre: "PLA Pro", precioRollo: 279 },
    { nombre: "PLA Matte", precioRollo: 289 },
  ],
  pesoRollo: 1000,        // g
  costoElectricidad: 2.8, // $/kWh
  consumoA1: 0.1,         // kW
  desgastePorHora: 6,     // $
  manoObraPorHora: 180,   // $
  empaqueBasico: 8,       // $
  tasaFallos: 5,          // %
  margenGanancia: 40,     // %
  comisionML: 16,         // %
  redondeo: 10,           // $
};

const CONFIG_KEY = "cotizador3d_config";
const HISTORIAL_KEY = "cotizador3d_historial";

function loadConfig() {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (!raw) return structuredClone(DEFAULT_CONFIG);
    const parsed = JSON.parse(raw);
    return { ...structuredClone(DEFAULT_CONFIG), ...parsed };
  } catch {
    return structuredClone(DEFAULT_CONFIG);
  }
}

function saveConfig(cfg) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(cfg));
}

function loadHistorial() {
  try {
    return JSON.parse(localStorage.getItem(HISTORIAL_KEY)) || [];
  } catch {
    return [];
  }
}

function saveHistorial(list) {
  localStorage.setItem(HISTORIAL_KEY, JSON.stringify(list));
}

let config = loadConfig();

// ---------- Utilidades ----------
const fmt = (n) => "$" + (Number(n) || 0).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const $ = (id) => document.getElementById(id);

function showToast(msg) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove("show"), 2200);
}

function ceilToMultiple(value, multiple) {
  if (!multiple || multiple <= 0) return value;
  return Math.ceil(value / multiple) * multiple;
}

// ---------- Cálculo (misma lógica que el Excel) ----------
function calcular(input) {
  const mat = config.materiales.find((m) => m.nombre === input.material) || config.materiales[0] || { precioRollo: 0 };
  const precioRollo = mat.precioRollo;

  const costoMaterial = ((input.pesoPieza + input.purgaAMS) * precioRollo) / config.pesoRollo;
  const electricidad = input.horas * config.consumoA1 * config.costoElectricidad;
  const desgaste = input.horas * config.desgastePorHora;
  const manoObra = (input.minPostproceso / 60) * config.manoObraPorHora;

  const subtotal = costoMaterial + electricidad + desgaste + manoObra;
  const ajusteFallos = subtotal * (config.tasaFallos / 100);
  const empaque = config.empaqueBasico;
  const costoTotalUnitario = subtotal + ajusteFallos + empaque;

  const precioSugerido = costoTotalUnitario * (1 + config.margenGanancia / 100);
  const precioML = precioSugerido / (1 - config.comisionML / 100);
  const precioFinalUnitario = input.plataforma === "ml" ? precioML : precioSugerido;
  const precioRedondeado = ceilToMultiple(precioFinalUnitario, config.redondeo);
  const gananciaUnitaria = precioRedondeado - costoTotalUnitario;

  const costoTotalPedido = costoTotalUnitario * input.cantidad;
  const precioTotalPedido = precioRedondeado * input.cantidad;
  const gananciaTotalPedido = precioTotalPedido - costoTotalPedido;

  return {
    precioRollo, costoMaterial, electricidad, desgaste, manoObra, subtotal,
    ajusteFallos, empaque, costoTotalUnitario, precioSugerido, precioML,
    precioFinalUnitario, precioRedondeado, gananciaUnitaria,
    costoTotalPedido, precioTotalPedido, gananciaTotalPedido,
  };
}

function readInput() {
  return {
    nombreModelo: $("nombreModelo").value.trim(),
    material: $("material").value,
    pesoPieza: parseFloat($("pesoPieza").value) || 0,
    purgaAMS: parseFloat($("purgaAMS").value) || 0,
    horas: parseFloat($("horas").value) || 0,
    minPostproceso: parseFloat($("minPostproceso").value) || 0,
    cantidad: parseInt($("cantidad").value) || 1,
    plataforma: $("plataforma").value,
    cliente: $("cliente").value.trim(),
  };
}

// ---------- Render ----------
function renderMaterialSelect() {
  const sel = $("material");
  const current = sel.value;
  sel.innerHTML = config.materiales
    .map((m) => `<option value="${m.nombre}">${m.nombre}</option>`)
    .join("");
  if (config.materiales.some((m) => m.nombre === current)) sel.value = current;
}

function renderBreakdown(r) {
  const rows = [
    ["Precio rollo del material", fmt(r.precioRollo)],
    ["Costo material unitario", fmt(r.costoMaterial)],
    ["Electricidad unitaria", fmt(r.electricidad)],
    ["Desgaste unitario", fmt(r.desgaste)],
    ["Mano de obra unitaria", fmt(r.manoObra)],
    ["Subtotal antes de fallos", fmt(r.subtotal)],
    ["Ajuste por tasa de fallos", fmt(r.ajusteFallos)],
    ["Empaque unitario", fmt(r.empaque)],
  ];
  $("breakdownBody").innerHTML = rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("")
    + `<tr class="total"><td>Costo total unitario</td><td>${fmt(r.costoTotalUnitario)}</td></tr>`;

  $("precioFinalUnitario").textContent = fmt(r.precioRedondeado);
  $("precioTotalPedido").textContent = fmt(r.precioTotalPedido);
  $("gananciaTotal").textContent = fmt(r.gananciaTotalPedido);
}

function recalc() {
  const input = readInput();
  const r = calcular(input);
  renderBreakdown(r);
  return { input, r };
}

// ---------- Cotización (texto) ----------
function buildQuoteText(input, r) {
  const fecha = new Date().toLocaleDateString("es-MX");
  const lines = [
    `COTIZACIÓN DE IMPRESIÓN 3D`,
    `Fecha: ${fecha}`,
    input.cliente ? `Cliente: ${input.cliente}` : null,
    ``,
    `Modelo: ${input.nombreModelo || "(sin nombre)"}`,
    `Material: ${input.material}`,
    `Cantidad: ${input.cantidad}`,
    `Plataforma: ${input.plataforma === "ml" ? "Mercado Libre" : "Venta directa"}`,
    ``,
    `Precio unitario: ${fmt(r.precioRedondeado)}`,
    `Precio total: ${fmt(r.precioTotalPedido)}`,
    ``,
    `¡Gracias por tu preferencia!`,
  ].filter((l) => l !== null);
  return lines.join("\n");
}

// ---------- Historial ----------
function renderHistorial() {
  const list = loadHistorial();
  $("historialBody").innerHTML = list
    .map(
      (h, i) => `<tr>
        <td>${h.fecha}</td><td>${h.modelo}</td><td>${h.cliente || "-"}</td>
        <td>${h.cantidad}</td><td>${fmt(h.costo)}</td><td>${fmt(h.venta)}</td><td>${fmt(h.venta - h.costo)}</td>
        <td><button class="icon-btn" data-idx="${i}" title="Eliminar">🗑</button></td>
      </tr>`
    )
    .join("") || `<tr><td colspan="8" style="color:var(--muted)">Sin registros aún</td></tr>`;

  $("historialBody").querySelectorAll(".icon-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const list = loadHistorial();
      list.splice(Number(btn.dataset.idx), 1);
      saveHistorial(list);
      renderHistorial();
    });
  });
}

function exportHistorialCSV() {
  const list = loadHistorial();
  const header = "Fecha,Modelo,Cliente,Cantidad,Costo,Venta,Ganancia";
  const rows = list.map((h) => [h.fecha, h.modelo, h.cliente || "", h.cantidad, h.costo.toFixed(2), h.venta.toFixed(2), (h.venta - h.costo).toFixed(2)].join(","));
  const csv = [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "historial_cotizaciones.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// ---------- Config modal ----------
function renderMaterialsTable() {
  $("materialsBody").innerHTML = config.materiales
    .map(
      (m, i) => `<tr>
        <td><input type="text" class="mat-name" data-idx="${i}" value="${m.nombre}"></td>
        <td><input type="number" step="0.01" class="mat-price" data-idx="${i}" value="${m.precioRollo}"></td>
        <td><button class="icon-btn" data-idx="${i}" title="Eliminar">🗑</button></td>
      </tr>`
    )
    .join("");

  $("materialsBody").querySelectorAll(".icon-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      config.materiales.splice(Number(btn.dataset.idx), 1);
      renderMaterialsTable();
    });
  });
}

function readConfigForm() {
  const names = [...document.querySelectorAll(".mat-name")];
  const prices = [...document.querySelectorAll(".mat-price")];
  const materiales = names
    .map((n, i) => ({ nombre: n.value.trim(), precioRollo: parseFloat(prices[i].value) || 0 }))
    .filter((m) => m.nombre);

  return {
    materiales: materiales.length ? materiales : structuredClone(DEFAULT_CONFIG.materiales),
    pesoRollo: parseFloat($("cfgPesoRollo").value) || DEFAULT_CONFIG.pesoRollo,
    costoElectricidad: parseFloat($("cfgCostoElectricidad").value) || 0,
    consumoA1: parseFloat($("cfgConsumo").value) || 0,
    desgastePorHora: parseFloat($("cfgDesgaste").value) || 0,
    manoObraPorHora: parseFloat($("cfgManoObra").value) || 0,
    empaqueBasico: parseFloat($("cfgEmpaque").value) || 0,
    tasaFallos: parseFloat($("cfgFallos").value) || 0,
    margenGanancia: parseFloat($("cfgMargen").value) || 0,
    comisionML: parseFloat($("cfgComisionML").value) || 0,
    redondeo: parseFloat($("cfgRedondeo").value) || 1,
  };
}

function fillConfigForm() {
  $("cfgPesoRollo").value = config.pesoRollo;
  $("cfgCostoElectricidad").value = config.costoElectricidad;
  $("cfgConsumo").value = config.consumoA1;
  $("cfgDesgaste").value = config.desgastePorHora;
  $("cfgManoObra").value = config.manoObraPorHora;
  $("cfgEmpaque").value = config.empaqueBasico;
  $("cfgFallos").value = config.tasaFallos;
  $("cfgMargen").value = config.margenGanancia;
  $("cfgComisionML").value = config.comisionML;
  $("cfgRedondeo").value = config.redondeo;
  renderMaterialsTable();
}

// ---------- Modales ----------
function openModal(id) { $(id).hidden = false; }
function closeModal(id) { $(id).hidden = true; }

document.querySelectorAll("[data-close]").forEach((btn) =>
  btn.addEventListener("click", () => closeModal(btn.dataset.close))
);
document.querySelectorAll(".modal").forEach((modal) =>
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.hidden = true; })
);

// ---------- Eventos ----------
$("quoteForm").addEventListener("input", recalc);

$("btnConfig").addEventListener("click", () => {
  fillConfigForm();
  openModal("configModal");
});

$("btnAddMaterial").addEventListener("click", () => {
  config.materiales.push({ nombre: "", precioRollo: 0 });
  renderMaterialsTable();
});

$("btnSaveConfig").addEventListener("click", () => {
  config = readConfigForm();
  saveConfig(config);
  renderMaterialSelect();
  recalc();
  closeModal("configModal");
});

$("btnResetConfig").addEventListener("click", () => {
  config = structuredClone(DEFAULT_CONFIG);
  fillConfigForm();
});

$("btnHistorial").addEventListener("click", () => {
  renderHistorial();
  resetClearButton();
  openModal("historialModal");
});

function resetClearButton() {
  const btn = $("btnClearHistorial");
  delete btn.dataset.armed;
  btn.textContent = "Borrar historial";
}

$("btnClearHistorial").addEventListener("click", () => {
  const btn = $("btnClearHistorial");
  if (!btn.dataset.armed) {
    btn.dataset.armed = "1";
    btn.textContent = "Confirmar borrado ✓";
    return;
  }
  resetClearButton();
  saveHistorial([]);
  renderHistorial();
});

$("btnExportHistorial").addEventListener("click", exportHistorialCSV);

$("btnGenerar").addEventListener("click", () => {
  const { input, r } = recalc();
  $("quoteText").textContent = buildQuoteText(input, r);
  $("quoteText").hidden = false;
});

$("btnCopiar").addEventListener("click", async () => {
  const { input, r } = recalc();
  const text = buildQuoteText(input, r);
  $("quoteText").textContent = text;
  $("quoteText").hidden = false;
  try {
    await navigator.clipboard.writeText(text);
    $("btnCopiar").textContent = "¡Copiado!";
    setTimeout(() => ($("btnCopiar").textContent = "Copiar texto"), 1500);
  } catch {
    showToast("No se pudo copiar automáticamente. Selecciona el texto manualmente.");
  }
});

$("btnWhatsapp").addEventListener("click", () => {
  const { input, r } = recalc();
  const text = buildQuoteText(input, r);
  const url = "https://wa.me/?text=" + encodeURIComponent(text);
  window.open(url, "_blank");
});

$("btnImprimir").addEventListener("click", () => {
  const { input, r } = recalc();
  $("quoteText").textContent = buildQuoteText(input, r);
  $("quoteText").hidden = false;
  window.print();
});

$("btnGuardar").addEventListener("click", () => {
  const { input, r } = recalc();
  const list = loadHistorial();
  list.unshift({
    fecha: new Date().toLocaleDateString("es-MX"),
    modelo: input.nombreModelo || "(sin nombre)",
    cliente: input.cliente,
    cantidad: input.cantidad,
    costo: r.costoTotalPedido,
    venta: r.precioTotalPedido,
  });
  saveHistorial(list);
  showToast("Cotización guardada en el historial.");
});

// ---------- Init ----------
renderMaterialSelect();
recalc();
