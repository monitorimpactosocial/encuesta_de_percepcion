// =========================================================
// ESTADO GLOBAL
// =========================================================
let currentData = [];
let charts = {};
let leafletMap = null;
let mapLayers = {};
let dynamicLayers = [];
let mapLegend = null;
let mapInitialized = false;

// ─── Utilidades ───────────────────────────────────────────
// Debounce: evita re-renders en cascada al cambiar filtros
function debounce(fn, delay) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

// Loader overlay
function showLoader() {
    const el = document.getElementById('loader-overlay');
    if (el) el.classList.add('active');
}
function hideLoader() {
    const el = document.getElementById('loader-overlay');
    if (el) el.classList.remove('active');
}

// countUp: anima un número desde 0 hasta target
function countUp(el, target, suffix = '', decimals = 0) {
    if (!el) return;
    const start = Date.now();
    const duration = 500; // ms
    el.classList.add('kpi-anim');
    const step = () => {
        const elapsed = Date.now() - start;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        const current = parseFloat((target * ease).toFixed(decimals));
        el.textContent = (decimals > 0 ? current.toFixed(decimals) : current) + suffix;
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = (decimals > 0 ? parseFloat(target).toFixed(decimals) : target) + suffix;
    };
    requestAnimationFrame(step);
}

// ESTADOS DE FILTROS (Múltiples selecciones permitidas por categoría)
let activeFilters = {
    'es_panel': new Set(),
    'percepción_clasificada': new Set(),
    'año': new Set(),
    'género': new Set(),
    'edad': new Set(),
    'nse': new Set(),
    'comunidad': new Set()
};

// CONFIGURACIÓN CHART.JS GLOBALES
Chart.defaults.color = '#475569'; // Color de fuente oscuro para Light Theme
Chart.defaults.font.size = 13;    // Aumento del tamaño para legibilidad de ejes
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.register(ChartDataLabels);

// ARRAYS DE VARIABLES A GRAFICAR (Conteo de presencias en strings)
const configAspectosPositivos = ['tranquilidad', 'seguridad', 'la gente', 'oferta laboral', 'desarrollo del sector comercial y servicios', 'ambiente paisaje'];
const configAspectosNegativos = ['inseguridad', 'consumo de drogas', 'poca oferta laboral', 'venta de drogas', 'violencia'];
const configExpectativas = ['más puestos de trabajo para personas de la zona', 'mejoras o nuevos caminos o rutas en zonas aledañas', 'nuevos comercios alrededor de la planta', 'formación laboral profesional de personas'];
const configMedios = ['radio', 'tv', 'redes sociales', 'medios de prensa', 'amigos conocidos', 'colaboradores de paracel que visitaron tu comunidad'];
const configOcupacion = ['no trabaja actualmente', 'funcionario público', 'empleado a tiempo completo', 'trabajador independiente', 'trabajador por jornal a destajo', 'propietario patrón', 'estudiante'];

// COLUMNAS DIRECTAS PARA AGRUPAR (Pie/Bar normal por categorías únicas)
const colTemores = 'un temor';
const colEstudios = 'estudios'; // fallback a nivel_de_estudios si rename aplicado
const colIngresos = 'podría indicarnos en qué rango se encuentra sus ingresos económicos familiaresesto quiere decir la suma de lo que ganan todas las personas que trabajan en la casa';

// CONSTANTES Y COLORES DE GRÁFICOS
const yearColors = {
    '2022': { bg: 'rgba(0, 240, 255, 0.75)', border: 'rgba(0, 240, 255, 1)' }, // Cyan Neon
    '2023': { bg: 'rgba(255, 0, 128, 0.75)', border: 'rgba(255, 0, 128, 1)' }, // Magenta Neon
    '2024': { bg: 'rgba(144, 255, 0, 0.75)', border: 'rgba(144, 255, 0, 1)' }, // Lime Neon
    '2025': { bg: 'rgba(255, 165, 0, 0.75)', border: 'rgba(255, 140, 0, 1)' }  // Orange Neon
};
const defaultColor = { bg: 'rgba(0, 240, 255, 0.75)', border: 'rgba(0, 240, 255, 1)' };

// =========================================================
// INICIALIZACIÓN
// =========================================================
document.addEventListener("DOMContentLoaded", () => {

    // ─── Tema persistente ────────────────────────────────────
    const savedTheme = localStorage.getItem('paracel_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const themeBtn2 = document.getElementById('btn-theme');
    if (themeBtn2) themeBtn2.innerText = savedTheme === 'dark' ? '☀️ Light' : '🌙 Dark';

    // ─── LOGIN STATE ─────────────────────────────────────────
    const loginForm  = document.getElementById('login-form');
    const inputUser  = document.getElementById('username');
    const inputPass  = document.getElementById('password');
    const loginError = document.getElementById('login-error');

    if (localStorage.getItem('paracel_logged') === 'true') {
        showDashboard();
    } else {
        if (inputUser) inputUser.focus();
    }

    const doLogin = () => {
        if (inputUser.value === 'user' && inputPass.value === '123') {
            localStorage.setItem('paracel_logged', 'true');
            loginError.style.display = 'none';
            showDashboard();
        } else {
            loginError.style.display = 'block';
            inputPass.select();
        }
    };

    if (loginForm) {
        loginForm.addEventListener('submit', (e) => { e.preventDefault(); doLogin(); });
    }

    document.getElementById('btn-logout').addEventListener('click', () => {
        localStorage.removeItem("paracel_logged");
        location.reload();
    });

    document.getElementById('btn-reset')?.addEventListener('click', () => {
        activeFilters = { 'es_panel': new Set(), 'percepción_clasificada': new Set(), 'año': new Set(), 'género': new Set(), 'edad': new Set(), 'nse': new Set(), 'comunidad': new Set() };
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        updateDashboard();
    });

    // SISTEMA DE TABS (PESTAÑAS)
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remover active de todos
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.style.display = 'none');

            // Activar el elegido
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).style.display = 'flex';

            // Redibujar gráficos para solucionar bug de canvas 0x0 en divs ocultos (Requerimos setTimeout para esperar el layout rendering nativo)
            setTimeout(() => {
                if (targetId === 'tab-mapas') {
                    initLeafletMap();
                } else {
                    debouncedUpdate();
                }
            }, 50);
        });
    });

    // FUNCIONES PRINCIPALES
    function showDashboard() {
        document.getElementById('login-screen').style.display = "none";
        document.getElementById('dashboard-screen').style.display = "flex";

        // Pre-procesar columna de percepción
        // Si ya viene 'percepción_clasificada' con valor válido (del script de exportación), usarla directamente
        encuestasData.forEach(d => {
            const ya = (d['percepción_clasificada'] ?? '').toString().trim().toLowerCase();
            if (ya.includes('posit') || ya.includes('negat') || ya.includes('neutr')) {
                if (ya.includes('posit')) d['percepción_clasificada'] = 'Positiva';
                else if (ya.includes('negat')) d['percepción_clasificada'] = 'Negativa';
                else d['percepción_clasificada'] = 'Neutra';
                return;
            }
            // Fallback: intentar derivarla de percepcion_final u otras columnas
            const pf = (d['percepcion_final'] ?? d['percepción_final'] ?? d['percepcion'] ?? d['percepción'] ?? '').toString().trim().toLowerCase();
            if (pf.includes('posit')) d['percepción_clasificada'] = 'Positiva';
            else if (pf.includes('negat')) d['percepción_clasificada'] = 'Negativa';
            else d['percepción_clasificada'] = 'Neutra';
        });
// Crear botones de filtros
        createFilterButtons('filter-muestra', 'es_panel');
        createFilterButtons('filter-percepcion', 'percepción_clasificada');
        createFilterButtons('filter-anio', 'año');
        createFilterButtons('filter-genero', 'género');
        createFilterButtons('filter-edad', 'edad');
        createFilterButtons('filter-nse', 'nse');
        createFilterButtons('filter-comunidad', 'comunidad');

        // Primer render general
        updateDashboard();
    }

    function createFilterButtons(containerId, colName) {
        const container = document.getElementById(containerId);
        container.innerHTML = ''; // limpiar

        // Extraer valores únicos válidos (convertirlos a minúscula para la variable del sistema)
        const uniqueValues = [...new Set(encuestasData.map(d => String(d[colName]).toLowerCase()))]
            .filter(v => v !== null && v !== undefined && v !== "" && v !== "nan" && v !== "ninguno/a")
            .sort();

        uniqueValues.forEach(val => {
            const btn = document.createElement('button');
            btn.className = 'filter-btn';
            btn.dataset.col = colName;
            btn.dataset.val = String(val);
            btn.innerText = String(val).charAt(0).toUpperCase() + String(val).slice(1);

            btn.addEventListener('click', (e) => {
                const isMultiSelect = e.ctrlKey || e.metaKey;
                const vStr = String(val);

                if (!isMultiSelect) {
                    activeFilters[colName].clear();
                    container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    activeFilters[colName].add(vStr);
                    btn.classList.add('active');
                } else {
                    if (activeFilters[colName].has(vStr)) {
                        activeFilters[colName].delete(vStr);
                        btn.classList.remove('active');
                    } else {
                        activeFilters[colName].add(vStr);
                        btn.classList.add('active');
                    }
                }
                debouncedUpdate();
            });

            container.appendChild(btn);
        });
    }

    // ─── Exportar PNG ─────────────────────────────────────────
    document.getElementById('btn-export')?.addEventListener('click', () => {
        const activeTab = document.querySelector('.tab-content.active');
        if (!activeTab) return;
        const dateStr = new Date().toISOString().slice(0, 10);
        const yearFilter = activeFilters['año'] && activeFilters['año'].size > 0
            ? Array.from(activeFilters['año']).join('-')
            : 'todos';
        activeTab.querySelectorAll('canvas').forEach((canvas, idx) => {
            const link = document.createElement('a');
            link.download = `Percepcion_Paracel_${yearFilter}_${dateStr}_fig${idx + 1}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        });
    });

    
    // Botón Informe Word (DOCX) para el filtro actual
    document.getElementById('btn-word')?.addEventListener('click', async () => {
        try {
            const activeTab = document.querySelector('.tab-content.active');
            if (!activeTab) return;

            // Dataset filtrado actual
            const dataFiltered = applyFilters(encuestasData);

            if (!dataFiltered || dataFiltered.length === 0) {
                alert('No hay datos para el filtro actual, ajuste los filtros e intente nuevamente.');
                return;
            }

            // --- Utilidades ---
            const norm = (x) => (x ?? '').toString().trim();
            const pct = (x, n) => n ? (100 * x / n) : 0;

            // --- Resumen de filtros ---
            const filtros = [];
            Object.keys(activeFilters).forEach(k => {
                if (activeFilters[k] && activeFilters[k].size > 0) {
                    filtros.push(`${k}: ${Array.from(activeFilters[k]).join(', ')}`);
                }
            });

            // --- KPIs principales ---
            const n = dataFiltered.length;
            const counts = { Positiva: 0, Negativa: 0, Neutra: 0 };
            dataFiltered.forEach(d => {
                const p = norm(d['percepción_clasificada'] || d['percepcion_final'] || d['percepcion_final']).toLowerCase();
                if (p.includes('posit')) counts.Positiva++;
                else if (p.includes('negat')) counts.Negativa++;
                else counts.Neutra++;
            });

            const balance = pct(counts.Positiva, n) - pct(counts.Negativa, n);

            // --- Evolución por año ---
            const byYear = {};
            dataFiltered.forEach(d => {
                const y = norm(d['año'] || d['ano'] || d['year']);
                if (!y) return;
                if (!byYear[y]) byYear[y] = { n: 0, Positiva: 0, Negativa: 0, Neutra: 0 };
                byYear[y].n++;
                const p = norm(d['percepción_clasificada'] || d['percepcion_final'] || d['percepcion_final']).toLowerCase();
                if (p.includes('posit')) byYear[y].Positiva++;
                else if (p.includes('negat')) byYear[y].Negativa++;
                else byYear[y].Neutra++;
            });
            const years = Object.keys(byYear).sort();

            // --- Top comunidades por balance (si corresponde) ---
            const byCom = {};
            dataFiltered.forEach(d => {
                const c = norm(d['comunidad']);
                if (!c) return;
                if (!byCom[c]) byCom[c] = { n: 0, Positiva: 0, Negativa: 0, Neutra: 0 };
                byCom[c].n++;
                const p = norm(d['percepción_clasificada'] || d['percepcion_final'] || d['percepcion_final']).toLowerCase();
                if (p.includes('posit')) byCom[c].Positiva++;
                else if (p.includes('negat')) byCom[c].Negativa++;
                else byCom[c].Neutra++;
            });
            const topCom = Object.entries(byCom)
                .filter(([_, v]) => v.n >= 8) // mínimo operativo para evitar volatilidad extrema
                .map(([k, v]) => {
                    const pos = pct(v.Positiva, v.n);
                    const neg = pct(v.Negativa, v.n);
                    return [k, v.n, pos, neg, (pos - neg)];
                })
                .sort((a, b) => b[4] - a[4])
                .slice(0, 10);

            // --- Capturar figuras del tab activo (canvases) ---
            const canvases = Array.from(activeTab.querySelectorAll('canvas'));
            const images = canvases
                .map(c => {
                    try { return c.toDataURL('image/png'); } catch (_) { return null; }
                })
                .filter(Boolean);

            // --- Construcción DOCX ---
            const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType, ImageRun } = window.docx;

            const para = (text, opts = {}) => new Paragraph({
                children: [new TextRun({ text, ...opts })]
            });

            const h = (text, level = HeadingLevel.HEADING_1) => new Paragraph({
                text,
                heading: level
            });

            const cell = (text) => new TableCell({
                children: [para(text)],
                width: { size: 25, type: WidthType.PERCENTAGE }
            });

            const tableFromRows = (rows) => new Table({
                rows: rows.map(r => new TableRow({ children: r.map(x => cell(String(x))) })),
                width: { size: 100, type: WidthType.PERCENTAGE }
            });

            const docChildren = [];
            docChildren.push(h('PARACEL · Informe de Percepción (Filtro actual)', HeadingLevel.HEADING_1));
            docChildren.push(new Paragraph({ text: `Fecha de generación: ${new Date().toLocaleString()}` }));

            if (filtros.length > 0) {
                docChildren.push(h('Filtros aplicados', HeadingLevel.HEADING_2));
                filtros.forEach(f => docChildren.push(new Paragraph({ text: `• ${f}` })));
            }

            docChildren.push(h('Resumen ejecutivo', HeadingLevel.HEADING_2));
            docChildren.push(new Paragraph({
                children: [
                    new TextRun({ text: `Tamaño muestral efectivo (n): ${n}. ` }),
                    new TextRun({ text: `Positiva: ${pct(counts.Positiva, n).toFixed(1)}%. ` }),
                    new TextRun({ text: `Negativa: ${pct(counts.Negativa, n).toFixed(1)}%. ` }),
                    new TextRun({ text: `Neutra: ${pct(counts.Neutra, n).toFixed(1)}%. ` }),
                    new TextRun({ text: `Balance neto: ${balance.toFixed(1)} pp.` })
                ]
            }));

            docChildren.push(h('Distribución global', HeadingLevel.HEADING_2));
            docChildren.push(tableFromRows([
                ['Categoría', 'n', '%'],
                ['Positiva', counts.Positiva, pct(counts.Positiva, n).toFixed(1)],
                ['Negativa', counts.Negativa, pct(counts.Negativa, n).toFixed(1)],
                ['Neutra', counts.Neutra, pct(counts.Neutra, n).toFixed(1)],
            ]));

            if (years.length > 0) {
                docChildren.push(h('Evolución por año (dentro del filtro)', HeadingLevel.HEADING_2));
                const rows = [['Año', 'n', '% Pos', '% Neg', '% Neu', 'Balance (pp)']];
                years.forEach(y => {
                    const v = byYear[y];
                    const pos = pct(v.Positiva, v.n);
                    const neg = pct(v.Negativa, v.n);
                    const neu = pct(v.Neutra, v.n);
                    rows.push([y, v.n, pos.toFixed(1), neg.toFixed(1), neu.toFixed(1), (pos - neg).toFixed(1)]);
                });
                docChildren.push(tableFromRows(rows));
            }

            if (topCom.length > 0) {
                docChildren.push(h('Top 10 comunidades por balance neto (n≥8)', HeadingLevel.HEADING_2));
                const rows = [['Comunidad', 'n', '% Pos', '% Neg', 'Balance (pp)']];
                topCom.forEach(r => rows.push([r[0], r[1], r[2].toFixed(1), r[3].toFixed(1), r[4].toFixed(1)]));
                docChildren.push(tableFromRows(rows));
            }

            if (images.length > 0) {
                docChildren.push(h('Figuras', HeadingLevel.HEADING_2));
                for (const img of images.slice(0, 6)) { // límite prudente
                    const base64 = img.split(',')[1];
                    const buf = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
                    docChildren.push(new Paragraph({
                        children: [new ImageRun({ data: buf, transformation: { width: 620, height: 340 } })],
                        alignment: AlignmentType.CENTER
                    }));
                }
            }

            docChildren.push(h('Notas metodológicas', HeadingLevel.HEADING_2));
            docChildren.push(new Paragraph({
                text: 'Este informe describe resultados para el subconjunto de datos que cumple el filtro seleccionado. Si el levantamiento no es probabilístico, la interpretación debe ser descriptiva. Para comparaciones interanuales robustas, se recomienda consistencia de cobertura y ponderación.'
            }));

            const doc = new Document({ sections: [{ children: docChildren }] });
            const blob = await Packer.toBlob(doc);

            const y = (activeFilters['año'] && activeFilters['año'].size === 1) ? Array.from(activeFilters['año'])[0] : 'multi';
            const fileName = `Informe_Percepcion_Paracel_${y}_${new Date().toISOString().slice(0,10)}.docx`;
            saveAs(blob, fileName);
        } catch (err) {
            console.error(err);
            alert('Ocurrió un error al generar el informe Word. Revise la consola del navegador (F12) para más detalle.');
        }
    });

    // ─── Theme Toggle (con persistencia) ─────────────────────
    const themeBtn = document.getElementById('btn-theme');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const newTheme = isDark ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('paracel_theme', newTheme);
            themeBtn.innerText = newTheme === 'dark' ? '☀️ Light' : '🌙 Dark';
            debouncedUpdate();
        });
    }

    // ─── APLICAR FILTROS Y RECOMPUTAR GRÁFICOS ───────────────
    function updateDashboard() {
        showLoader();
        // Defer rendering to next frame so loader paints first
        requestAnimationFrame(() => {
            try {
                let filtered = encuestasData;

                for (const [colName, selectedSet] of Object.entries(activeFilters)) {
                    if (selectedSet.size > 0) {
                        filtered = filtered.filter(d =>
                            selectedSet.has(String(d[colName]).toLowerCase()) ||
                            selectedSet.has(String(d[colName]))
                        );
                    }
                }

                currentData = filtered;
                document.getElementById('total-encuestas').innerText = `📊 ${currentData.length} encuestas`;

                // RENDER MODULE 1
                renderKPIs(currentData);
                renderSingleColumnChart('chartComunidades', 'bar', 'comunidad');
                renderMultiColumnChart('chartPositivos', 'bar', 'Aspectos Positivos (%)', configAspectosPositivos);
                renderMultiColumnChart('chartNegativos', 'bar', 'Problemas / Negativos (%)', configAspectosNegativos);

                // RENDER MODULE 2
                renderMultiColumnChart('chartExpectativas', 'bar', 'Expectativas (%)', configExpectativas);
                renderMultiColumnChart('chartMedios', 'bar', 'Medios de Info. (%)', configMedios);
                renderSingleColumnChart('chartTemores', 'bar', colTemores);

                // RENDER MODULE 3
                renderSingleColumnChart('chartEstudios', 'bar', colEstudios);
                renderSingleColumnChart('chartIngresos', 'bar', colIngresos);
                renderMultiColumnChart('chartTrabajo', 'bar', 'Situación Laboral (%)', configOcupacion);

                // RENDER MODULE 4 (EVOLUCIÓN 2022-2025)
                renderEvolPositiva();
                renderMultiColumnChart('chartEvolFaltaLaboral', 'bar', 'Falta Oferta Laboral (%)', ['poca oferta laboral']);
                renderMultiColumnChart('chartEvolAtributos', 'bar', 'Atributos (%)', ['tranquilidad', 'la gente']);
                renderEvolProduccion();
                renderMultiColumnChart('chartEvolBeneficios', 'line', 'Beneficios (%)', ['puestos de trabajo para', 'caminos o rutas en zonas']);
                renderMultiColumnChart('chartEvolCanales', 'bar', 'Canales (%)', configMedios);

                // RENDER MODULE 5 (TABLA)
                renderDataTable(currentData);

                // RENDER MODULE 6 (MAPA GIS)
                if (leafletMap) updateMapColors();

            } finally {
                hideLoader();
            }
        });
    }

    // Versión con debounce (150 ms) para filtros rápidos
    const debouncedUpdate = debounce(updateDashboard, 150);

    // ─── KPIs CON ANIMACIÓN countUp ───────────────────────────
    function renderKPIs(data) {
        const elTotal   = document.getElementById('kpi-total');
        const elPos     = document.getElementById('kpi-positiva');
        const elProb    = document.getElementById('kpi-problema');
        const elAttr    = document.getElementById('kpi-atributo');

        if (!data || data.length === 0) {
            if (elTotal) elTotal.textContent = '0';
            if (elPos)   elPos.textContent   = '0%';
            if (elProb)  elProb.textContent   = '—';
            if (elAttr)  elAttr.textContent   = '—';
            return;
        }

        // 1. Total encuestas — animado
        countUp(elTotal, data.length);

        // 2. Percepción positiva — animado con 1 decimal
        const countPos = data.filter(d => d['percepción_clasificada'] === 'Positiva').length;
        const pctPos = (countPos / data.length) * 100;
        countUp(elPos, pctPos, '%', 1);

        // Helper fuzzy key
        function getFuzzyKey(obj, substring) {
            return Object.keys(obj).find(k => k.toLowerCase().includes(substring.toLowerCase())) || substring;
        }
        const bad = new Set(['undefined', 'null', '', 'ninguno', 'nan', 'false', '-']);

        // 3. Top Problema
        const problemas = {};
        data.forEach(d => {
            configAspectosNegativos.forEach(p => {
                const strV = String(d[getFuzzyKey(d, p)] ?? '').trim().toLowerCase();
                if (!bad.has(strV)) problemas[p] = (problemas[p] || 0) + 1;
            });
        });
        const topProblema = Object.keys(problemas).sort((a, b) => problemas[b] - problemas[a])[0];
        if (elProb) elProb.textContent = topProblema ? truncate(topProblema, 28) : 'N/A';

        // 4. Top Atributo
        const atributos = {};
        data.forEach(d => {
            configAspectosPositivos.forEach(a => {
                const strV = String(d[getFuzzyKey(d, a)] ?? '').trim().toLowerCase();
                if (!bad.has(strV)) atributos[a] = (atributos[a] || 0) + 1;
            });
        });
        const topAtributo = Object.keys(atributos).sort((a, b) => atributos[b] - atributos[a])[0];
        if (elAttr) elAttr.textContent = topAtributo ? truncate(topAtributo, 28) : 'N/A';
    }

    // Para contar presencias ("Sí") cruzando múltiples columnas
    function renderMultiColumnChart(canvasId, type, label, keysToCount) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (charts[canvasId]) charts[canvasId].destroy();

        let years = Array.from(activeFilters['año']);
        if (years.length === 0) {
            years = [...new Set(currentData.map(d => String(d['año'])))].filter(y => y !== 'undefined' && y !== 'null' && y !== 'NaN').sort();
        }

        let labels = keysToCount.map(k => truncate(k));
        let datasets = [];

        years.forEach(year => {
            let yearData = currentData.filter(d => String(d['año']) === year);
            const total = yearData.length;
            let dataPoints = [];

            keysToCount.forEach(keySubstring => {
                // Fuzzy Key Finder para sortear encondings raros
                let actualKey = Object.keys(currentData[0] || {}).find(k => k.toLowerCase().includes(keySubstring.toLowerCase())) || keySubstring;

                // Presencia: no vacío, no nulo, y si es numérico debe ser != 0
                let count = yearData.filter(d => {
                    let v = d[actualKey];
                    if (v === null || v === undefined) return false;
                    // Valores numéricos: 0 = ausencia
                    if (v === 0 || v === false || v === '0' || v === 'false') return false;
                    let strV = String(v).trim().toLowerCase();
                    if (strV === "" || strV === "-" || strV === "nan" || strV === "ninguno" || strV === "ninguna") return false;
                    return true;
                }).length;

                let pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                dataPoints.push(Number(pct));
            });

            let colorObj = yearColors[year] || defaultColor;

            datasets.push({
                label: `${year}`,
                data: dataPoints,
                backgroundColor: type === 'line' ? colorObj.bg.replace('0.7', '0.1') : colorObj.bg,
                borderColor: colorObj.border,
                borderWidth: 1,
                fill: type === 'line',
                tension: 0.3
            });
        });

        // --- ORDENAR DE MAYOR A MENOR SEGÚN EL ÚLTIMO AÑO DISPONIBLE ---
        if (type === 'bar' || type === 'horizontalBar' || type === 'pie') {
            // Referencia al data array del último año (datasets[datasets.length - 1])
            let refData = datasets[datasets.length - 1].data;

            // Crear array de índices ordenados descendentemente por los valores de refData
            let indices = Array.from(labels.keys()).sort((a, b) => refData[b] - refData[a]);

            // Reordenar las labels
            labels = indices.map(i => labels[i]);

            // Reordenar data points en todos los datasets
            datasets.forEach(ds => {
                ds.data = indices.map(i => ds.data[i]);
            });
        }

        drawChart(ctx, canvasId, type, labels, datasets);
    }

    // Para agrupar respuestas de 1 sola columna
    function renderSingleColumnChart(canvasId, type, colName) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (charts[canvasId]) charts[canvasId].destroy();

        let years = Array.from(activeFilters['año']);
        if (years.length === 0) {
            years = [...new Set(currentData.map(d => String(d['año'])))].filter(y => y !== 'undefined' && y !== 'null' && y !== 'NaN').sort();
        }

        // Obtener respuestas válidas históricamente
        let allValidAnswers = new Set();
        let globalCounts = {};
        currentData.forEach(d => {
            let v = d[colName];
            if (v === null || v === undefined) return;
            // Quitamos la comprobación isNaN porque un texto es isNaN(true)
            let strV = String(v).trim();
            if (strV.toLowerCase() === "nan" || strV === "" || strV === "-") return;
            allValidAnswers.add(strV);
            globalCounts[strV] = (globalCounts[strV] || 0) + 1;
        });

        // Ordenar respuestas de mayor a menor general
        let validAnswersArray = Array.from(allValidAnswers).sort((a, b) => globalCounts[b] - globalCounts[a]);
        let labels = validAnswersArray.map(k => truncate(k));

        let datasets = [];

        // Si es PIE interanual, lo convertimos a BARRA para que lado a lado funcione visualmente
        if (type === 'pie' && years.length > 1) {
            type = 'bar';
        }

        years.forEach(year => {
            let yearData = currentData.filter(d => String(d['año']) === year);

            let counts = {};
            let validTotal = 0;
            yearData.forEach(d => {
                let v = d[colName];
                if (v === null || v === undefined) return;
                let strV = String(v).trim();
                if (strV.toLowerCase() === "nan" || strV === "" || strV === "-") return;
                counts[strV] = (counts[strV] || 0) + 1;
                validTotal += 1;
            });

            const total = validTotal > 0 ? validTotal : 1; // Prevenir div por 0

            let dataPoints = validAnswersArray.map(ans => {
                let count = counts[ans] || 0;
                return ((count / total) * 100).toFixed(1);
            });

            let colorObj = yearColors[year] || defaultColor;

            // Paleta para pie simple y vibrante
            const pieBgColors = ['#00f0ff', '#ff007f', '#90ff00', '#ffea00', '#9d00ff', '#ff5e00', '#00ff73', '#00b8ff'];

            datasets.push({
                label: `${year}`, // Optimización UX: Sólo mostrar el año, la figura ya es autodescriptiva
                data: dataPoints,
                backgroundColor: type === 'pie' ? pieBgColors : colorObj.bg,
                borderColor: type === 'pie' ? '#0d1117' : colorObj.border,
                borderWidth: type === 'pie' ? 2 : 1,
                fill: false
            });
        });

        drawChart(ctx, canvasId, type, labels, datasets);
    }

    // CUSTOM RENDERS PARA TAB EVOLUCION
    function renderEvolPositiva() {
        const ctx = document.getElementById('chartEvolPositiva').getContext('2d');
        if (charts['chartEvolPositiva']) charts['chartEvolPositiva'].destroy();

        let years = Array.from(activeFilters['año']);
        if (years.length === 0) {
            years = [...new Set(currentData.map(d => String(d['año'])))].filter(y => y !== 'undefined' && y !== 'null' && y !== 'NaN').sort();
        }

        // Usar percepción_clasificada (ya pre-procesada en showDashboard), no heurística de columna
        const catColors = {
            Positiva: { bg: 'rgba(34,197,94,0.15)',  border: '#22c55e' },
            Negativa: { bg: 'rgba(239,68,68,0.15)',  border: '#ef4444' },
            Neutra:   { bg: 'rgba(148,163,184,0.15)', border: '#94a3b8' }
        };

        const datasets = ['Positiva', 'Neutra', 'Negativa'].map(cat => ({
            label: `${cat} (%)`,
            data: years.map(year => {
                const yd = currentData.filter(d => String(d['año']) === year);
                const total = yd.length;
                if (!total) return 0;
                const count = yd.filter(d => d['percepción_clasificada'] === cat).length;
                return Number(((count / total) * 100).toFixed(1));
            }),
            backgroundColor: catColors[cat].bg,
            borderColor: catColors[cat].border,
            borderWidth: 2,
            fill: cat === 'Positiva',
            tension: 0.3
        }));

        drawChart(ctx, 'chartEvolPositiva', 'line', years, datasets);
    }

    function renderEvolProduccion() {
        const ctx = document.getElementById('chartEvolProduccion').getContext('2d');
        if (charts['chartEvolProduccion']) charts['chartEvolProduccion'].destroy();

        let years = Array.from(activeFilters['año']);
        if (years.length === 0) {
            years = [...new Set(currentData.map(d => String(d['año'])))].filter(y => y !== 'undefined' && y !== 'null' && y !== 'NaN').sort();
        }

        let labels = ['No sabe / NS/NR', 'Celulosa', 'Eucalipto / Madera'];
        let datasets = [];

        years.forEach(year => {
            let yearData = currentData.filter(d => String(d['año']) === year);
            const total = yearData.length;

            let countNonsabe = 0;
            let countCelulosa = 0;
            let countEucalipto = 0;

            yearData.forEach(d => {
                let ans = String(d['que crees que producira la fabrica de paracel']).toLowerCase();
                if (ans.includes('no sabe') || ans.includes('ns nr') || ans.includes('ns/nr') || ans.includes('nan') || ans === '-') countNonsabe++;
                else if (ans.includes('celulosa') || ans.includes('papel')) countCelulosa++;
                else if (ans.includes('eucalipto') || ans.includes('madera')) countEucalipto++;
            });

            datasets.push({
                label: `Respuestas - ${year}`,
                data: total > 0 ? [
                    ((countNonsabe / total) * 100).toFixed(1),
                    ((countCelulosa / total) * 100).toFixed(1),
                    ((countEucalipto / total) * 100).toFixed(1)
                ] : [0, 0, 0],
                backgroundColor: (yearColors[year] || defaultColor).bg,
                borderColor: (yearColors[year] || defaultColor).border,
                borderWidth: 1
            });
        });

        drawChart(ctx, 'chartEvolProduccion', 'bar', labels, datasets);
    }

    // Motor de pintado genérico
    function drawChart(ctx, canvasId, type, labels, datasets) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const rawColor = isDark ? '#e2e8f0' : '#475569';
        const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
        const labelColor = isDark ? '#8b949e' : '#64748b';

        Chart.defaults.color = rawColor;

        charts[canvasId] = new Chart(ctx, {
            type: type,
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: (canvasId === 'chartEstudios' || canvasId === 'chartIngresos' || canvasId === 'chartTrabajo') ? 'y' : 'x',
                plugins: {
                    legend: {
                        display: true, // Mostrar leyenda siempre para identificar los años
                        position: 'top',
                        labels: {
                            color: rawColor,
                            font: { size: 11, family: "'Inter', sans-serif" },
                            padding: 20 // Espacio enorme entre los ítem de la leyenda y su caja delimitadora
                        }
                    },
                    datalabels: {
                        color: type === 'pie' ? '#fff' : rawColor,
                        anchor: type === 'pie' ? 'center' : 'end',
                        align: type === 'pie' ? 'center' : (type === 'line' ? 'top' : 'end'),
                        rotation: type === 'bar' ? -90 : 0, // <-- Gira las etiquetas verticales para salvar el ancho
                        formatter: function (value) { return value > 0 ? value + '%' : ''; },
                        font: { weight: 'bold', size: 10, family: "'Inter', sans-serif" },
                        display: function (context) {
                            let val = context.dataset.data[context.dataIndex];
                            return val >= 4.0;
                        }
                    }
                },
                scales: (type === 'bar' || type === 'line') ? {
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { color: labelColor, font: { size: 12 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: labelColor,
                            font: { size: 12 },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                } : {},
                layout: {
                    padding: { top: 10, bottom: 20, left: 10, right: 10 }
                }
            }
        });
    }

    function truncate(str) {
        let s = String(str).charAt(0).toUpperCase() + String(str).slice(1);
        if (s.length > 30) return s.substring(0, 30) + '...';
        return s;
    }

    // --- TABLA DE DATOS INTERACTIVA ---
    function renderDataTable(data) {
        const thead = document.getElementById('table-head-row');
        const tbody = document.getElementById('table-body');

        thead.innerHTML = '';
        tbody.innerHTML = '';

        if (!data || data.length === 0) return;

        // Seleccionar columnas clave para no saturar el DOM (max 12)
        const displayCols = ['año', 'id', 'género', 'edad', 'sector', 'comunidad', 'nse', 'es_panel', 'percepción_clasificada'];

        // Cabeceras
        displayCols.forEach(col => {
            const th = document.createElement('th');
            th.innerText = String(col).toUpperCase();
            th.style.padding = '12px 15px';
            th.style.borderBottom = '2px solid var(--border)';
            th.style.color = 'var(--text)';
            thead.appendChild(th);
        });

        // Filas (Limitado a 500 para rendimiento en Web, el export descarga todo)
        const limit = Math.min(data.length, 500);
        for (let i = 0; i < limit; i++) {
            const row = data[i];
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid var(--glass-border)';

            displayCols.forEach(col => {
                const td = document.createElement('td');
                let val = row[col];

                // Fallback de codificación para género
                if (col === 'género') {
                    val = row['género'] || row['genero'] || row['sexo'];
                }

                td.innerText = val !== undefined && val !== null ? val : '-';
                td.style.padding = '10px 15px';
                td.style.color = 'var(--text-sec)';
                td.style.fontSize = '13px';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        }
    }

    // --- EXPORTAR CSV ---
    document.getElementById('btn-export-csv').addEventListener('click', () => {
        if (!currentData || currentData.length === 0) {
            alert("No hay datos para exportar bajo los filtros actuales.");
            return;
        }

        // Exportamos todas las columnas del primer objeto para el archivo CSV real
        const allKeys = Object.keys(currentData[0]);
        let csvContent = "";

        // Cabecera CSV
        csvContent += allKeys.join(";") + "\r\n";

        // Data CSV
        currentData.forEach(row => {
            let rowArray = allKeys.map(k => {
                let val = row[k] !== null && row[k] !== undefined ? String(row[k]) : "";
                val = val.replace(/"/g, '""'); // Escape comillas
                if (val.includes(';') || val.includes('\n')) {
                    val = `"${val}"`;
                }
                return val;
            });
            csvContent += rowArray.join(";") + "\r\n";
        });

        const blob = new Blob(['\ufeff', csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const dateStr = new Date().toISOString().slice(0, 10);
        link.setAttribute('href', url);
        link.setAttribute('download', `Data_Percepcion_Paracel_${dateStr}_n${currentData.length}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });

    // --- MÓDULO GIS LEAFLET (HEAT MAP MEJORADO) ---
    let currentMapMetric = 'positiva'; // 'positiva' | 'temor' | 'balance'

    function initLeafletMap() {
        if (leafletMap) {
            leafletMap.invalidateSize();
            updateMapColors();
            return;
        }

        leafletMap = L.map('map-container').setView([-23.4, -57.4], 8);

        const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri'
        }).addTo(leafletMap);

        const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap & CartoDB'
        });

        // Inyectar selector de métrica + panel estadísticas en el tab de mapas
        _injectMapControls();

        const styleDistritos   = { color: "#ffffff", weight: 1, fillOpacity: 0.05, dashArray: '5, 5' };
        const stylePropiedades = { color: "#90ff00", weight: 2, fillColor: "#90ff00", fillOpacity: 0.2 };
        const styleIndigenas   = { color: "#ff007f", weight: 2, fillColor: "#ff007f", fillOpacity: 0.4 };
        const styleComunidades = { color: "#00f0ff", weight: 2, fillColor: "#00f0ff", fillOpacity: 0.3 };

        mapLayers = {};
        dynamicLayers = [];
        let basemaps = { "Satélite (Esri)": satelliteLayer, "Calles Oscuro (CartoDB)": darkLayer };
        let overlays = {};

        if (typeof mapasData !== 'undefined') {
            if (mapasData['distritos_paracel']) {
                let layer = L.geoJSON(mapasData['distritos_paracel'], {
                    style: styleDistritos,
                    onEachFeature: (feature, layer) => {
                        let name = feature.properties.DISTRITO || feature.properties.DIST_DESC_ || 'N/A';
                        layer.options._geoName = name;
                        layer.bindPopup(`<b>Distrito:</b> ${name}`);
                    }
                }).addTo(leafletMap);
                overlays['Límites Distritales'] = layer;
                dynamicLayers.push({ layer, defaultColor: '#ffffff' });
            }

            if (mapasData['propiedades_forestales']) {
                let layer = L.geoJSON(mapasData['propiedades_forestales'], {
                    style: stylePropiedades,
                    onEachFeature: (feature, layer) => {
                        layer.bindPopup(`<b>Estancia:</b> ${feature.properties.Estancia || 'N/A'} <br><b>Área:</b> ${feature.properties.Area || 'N/A'} Ha`);
                    }
                }).addTo(leafletMap);
                overlays['Núcleos Forestales PARACEL'] = layer;
            }

            if (mapasData['componentes_industriales']) {
                let layer = L.geoJSON(mapasData['componentes_industriales'], {
                    style: { color: "#ffea00", weight: 3, fillColor: "#ffea00", fillOpacity: 0.6 },
                    onEachFeature: (feature, layer) => {
                        layer.bindPopup(`<b>Instalación:</b> ${feature.properties.proyecto || feature.properties.Name || 'Componente Industrial'}`);
                    }
                }).addTo(leafletMap);
                overlays['Planta Industrial y Puertos'] = layer;
            }

            if (mapasData['comunidades_indigenas']) {
                let layer = L.geoJSON(mapasData['comunidades_indigenas'], {
                    style: styleIndigenas,
                    onEachFeature: (feature, layer) => {
                        let name = feature.properties.COM_DESC || feature.properties.BARLO_DESC || 'N/A';
                        layer.options._geoName = name;
                        layer.bindPopup(`<b>Comunidad Indígena:</b> ${name}`);
                    }
                }).addTo(leafletMap);
                overlays['Comunidades Indígenas'] = layer;
                dynamicLayers.push({ layer, defaultColor: '#ff007f' });
            }

            let comunidadesLayer = L.layerGroup().addTo(leafletMap);
            if (mapasData['comunidades_industriales']) {
                let sub = L.geoJSON(mapasData['comunidades_industriales'], {
                    style: styleComunidades,
                    onEachFeature: (feature, layer) => {
                        let name = feature.properties.Localidade || feature.properties.Localidad || 'N/A';
                        layer.options._geoName = name;
                        layer.bindPopup(`<b>Comunidad (Z. Ind.):</b> ${name}`);
                    }
                }).addTo(comunidadesLayer);
                dynamicLayers.push({ layer: sub, defaultColor: '#00f0ff' });
            }
            if (mapasData['comunidades_forestales']) {
                let sub = L.geoJSON(mapasData['comunidades_forestales'], {
                    style: styleComunidades,
                    onEachFeature: (feature, layer) => {
                        let name = feature.properties.Localidad || feature.properties.Localidade || 'N/A';
                        layer.options._geoName = name;
                        layer.bindPopup(`<b>Comunidad (Z. For.):</b> ${name}`);
                    }
                }).addTo(comunidadesLayer);
                dynamicLayers.push({ layer: sub, defaultColor: '#00f0ff' });
            }
            overlays['Comunidades de Influencia Formal'] = comunidadesLayer;

            let barriosLayer = L.layerGroup();
            const barStyle = { color: "#ffffff", weight: 0.5, fillColor: "#ffffff", fillOpacity: 0.1 };
            ['barrios_concepcion', 'barrios_amambay'].forEach(key => {
                if (mapasData[key]) {
                    let sub = L.geoJSON(mapasData[key], {
                        style: barStyle,
                        onEachFeature: (feature, layer) => {
                            let name = feature.properties.BARLO_DESC || feature.properties.BARRIO || feature.properties.BAR_LOC || 'N/A';
                            layer.options._geoName = name;
                            layer.bindPopup(`<b>Barrio:</b> ${name}`);
                        }
                    }).addTo(barriosLayer);
                    dynamicLayers.push({ layer: sub, defaultColor: '#ffffff' });
                }
            });
            overlays['Capa Urbana / Barrios Centrales'] = barriosLayer;

        } else {
            console.warn("mapasData no detectado. El mapa de calor funcionará cuando se carguen las capas GIS.");
        }

        L.control.layers(basemaps, overlays, { collapsed: false }).addTo(leafletMap);
        leafletMap.invalidateSize();
        updateMapColors();
    }

    // Inyecta controles de métrica y panel de estadísticas en el contenedor del mapa
    function _injectMapControls() {
        const tabMapas = document.getElementById('tab-mapas');
        if (!tabMapas || document.getElementById('map-metric-selector')) return;

        // Inserta selector de métrica arriba del mapa
        const selectorHTML = `
        <div id="map-metric-selector" style="
            display:flex; gap:10px; padding:12px 16px 8px;
            flex-wrap:wrap; align-items:center; border-bottom:1px solid var(--glass-border);
            background:var(--glass-bg); backdrop-filter:blur(8px);
        ">
            <span style="font-weight:700; color:var(--text); font-size:13px;">🗺️ Mapa de Calor:</span>
            <button class="map-metric-btn active" data-metric="positiva"
                style="padding:6px 14px; border-radius:6px; border:1px solid #22c55e; background:rgba(34,197,94,0.2); color:#22c55e; cursor:pointer; font-size:12px; font-weight:600;">
                ✅ Percepción Positiva
            </button>
            <button class="map-metric-btn" data-metric="temor"
                style="padding:6px 14px; border-radius:6px; border:1px solid #ef4444; background:transparent; color:var(--text-sec); cursor:pointer; font-size:12px; font-weight:600;">
                ⚠️ Presencia de Temores
            </button>
            <button class="map-metric-btn" data-metric="balance"
                style="padding:6px 14px; border-radius:6px; border:1px solid #06b6d4; background:transparent; color:var(--text-sec); cursor:pointer; font-size:12px; font-weight:600;">
                ⚖️ Balance Neto (Pos−Neg)
            </button>
            <span id="map-sample-info" style="margin-left:auto; font-size:11px; color:var(--text-sec); font-style:italic;"></span>
        </div>
        <div id="map-stats-panel" style="
            display:flex; height:calc(100% - 48px); overflow:hidden;
        ">
            <div id="map-community-list" style="
                width:260px; min-width:220px; overflow-y:auto;
                padding:10px 6px; border-right:1px solid var(--glass-border);
                background:rgba(0,0,0,0.18); font-size:12px;
                scrollbar-width:thin;
            ">
                <div style="font-weight:700; color:var(--text); margin-bottom:8px; padding:0 6px 6px; border-bottom:1px solid var(--glass-border);">
                    📊 Ranking por Comunidad
                </div>
                <div id="map-community-rows" style="display:flex;flex-direction:column;gap:4px;"></div>
            </div>
            <div id="map-container" style="flex:1; min-height:400px;"></div>
        </div>`;

        // Reemplaza el map-container si ya existe como hijo directo
        const existing = tabMapas.querySelector('#map-container');
        if (existing && existing.parentElement === tabMapas) {
            existing.outerHTML = selectorHTML;
        } else {
            tabMapas.insertAdjacentHTML('afterbegin', selectorHTML);
        }

        // Event listeners para botones de métrica
        tabMapas.querySelectorAll('.map-metric-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                tabMapas.querySelectorAll('.map-metric-btn').forEach(b => {
                    b.style.background = 'transparent';
                    b.style.color = 'var(--text-sec)';
                    b.classList.remove('active');
                });
                btn.classList.add('active');
                btn.style.background = currentMapMetric === 'positiva' ? 'rgba(34,197,94,0.2)' :
                                       currentMapMetric === 'temor'    ? 'rgba(239,68,68,0.2)'  :
                                                                          'rgba(6,182,212,0.2)';
                btn.style.color = currentMapMetric === 'positiva' ? '#22c55e' :
                                  currentMapMetric === 'temor'    ? '#ef4444' : '#06b6d4';
                currentMapMetric = btn.dataset.metric;
                // Estilo activo para el botón recién seleccionado
                const colors = { positiva: ['rgba(34,197,94,0.2)', '#22c55e'], temor: ['rgba(239,68,68,0.2)', '#ef4444'], balance: ['rgba(6,182,212,0.2)', '#06b6d4'] };
                const [bg, fg] = colors[currentMapMetric];
                btn.style.background = bg;
                btn.style.color = fg;
                updateMapColors();
            });
        });
    }

    // Calcula estadísticas por comunidad desde currentData
    function _computeMapStats() {
        const statsRaw = {};
        const MIN_N = 5; // mínimo para mostrar dato en mapa

        currentData.forEach(d => {
            const com = String(d['comunidad'] || d['distrito'] || d['barrio'] || '').trim();
            if (!com || com.toLowerCase() === 'nan' || com === '-') return;

            if (!statsRaw[com]) statsRaw[com] = { total: 0, pos: 0, neg: 0, temor: 0 };
            statsRaw[com].total++;
            const perc = d['percepción_clasificada'] || '';
            if (perc === 'Positiva') statsRaw[com].pos++;
            if (perc === 'Negativa') statsRaw[com].neg++;
            // Temor: si columna 'es_panel' no aplica; usamos percepción negativa como proxy básico
            // o la columna 'un temor' si tiene valor no vacío/0
            const tVal = d['un temor'] ?? d['tiene_temor'] ?? '';
            const tStr = String(tVal).toLowerCase().trim();
            const hasTemor = tVal !== 0 && tVal !== false && tStr !== '' && tStr !== '0' && tStr !== 'false' && tStr !== 'nan' && tStr !== 'ninguno' && tStr !== 'ninguna';
            if (hasTemor) statsRaw[com].temor++;
        });

        const stats = {};
        for (const com in statsRaw) {
            const s = statsRaw[com];
            if (s.total < MIN_N) continue;
            stats[com] = {
                n: s.total,
                pctPos:    (s.pos    / s.total) * 100,
                pctNeg:    (s.neg    / s.total) * 100,
                pctTemor:  (s.temor  / s.total) * 100,
                balance:   ((s.pos - s.neg) / s.total) * 100
            };
        }
        return stats;
    }

    // Normaliza nombre para fuzzy matching
    function _normGeo(name) {
        if (!name) return '';
        return String(name).toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9]/g, '');
    }

    // Semáforo NAUTA: umbral 70 / 50 (alineado al reporte R)
    function _getHeatColor(value, metric) {
        if (metric === 'temor') {
            // Para temores: invertir — más temor = más rojo
            if (value >= 30) return '#ef4444';
            if (value >= 15) return '#f59e0b';
            return '#22c55e';
        }
        // Para positiva y balance (NAUTA: Favorable ≥70, Atención 50-70, Crítico <50)
        if (value >= 70) return '#22c55e';  // Verde — Favorable
        if (value >= 50) return '#f59e0b';  // Ámbar — Atención
        return '#ef4444';                   // Rojo   — Crítico
    }

    // Genera el HTML del popup para una comunidad con datos
    function _buildPopup(name, s, metric) {
        const estado = metric === 'temor'
            ? (s.pctTemor >= 30 ? 'Crítico' : s.pctTemor >= 15 ? 'Atención' : 'Favorable')
            : (s.pctPos >= 70 ? 'Favorable' : s.pctPos >= 50 ? 'Atención' : 'Crítico');
        const stateColors = { Favorable: '#22c55e', Atención: '#f59e0b', Crítico: '#ef4444' };
        const col = stateColors[estado];

        return `
        <div style="min-width:200px; font-family:Inter,sans-serif; font-size:13px;">
            <div style="font-weight:700; font-size:15px; margin-bottom:8px; border-bottom:1px solid #ddd; padding-bottom:6px;">
                📍 ${name}
            </div>
            <div style="display:grid; grid-template-columns:auto 1fr; gap:4px 10px; line-height:1.6;">
                <span style="color:#777;">Base (n)</span>   <b>${s.n}</b>
                <span style="color:#777;">Percepción +</span> <b style="color:#22c55e;">${s.pctPos.toFixed(1)}%</b>
                <span style="color:#777;">Percepción –</span> <b style="color:#ef4444;">${s.pctNeg.toFixed(1)}%</b>
                <span style="color:#777;">Con temor</span>  <b style="color:#f59e0b;">${s.pctTemor.toFixed(1)}%</b>
                <span style="color:#777;">Balance</span>    <b>${s.balance >= 0 ? '+' : ''}${s.balance.toFixed(1)} pp</b>
            </div>
            <div style="margin-top:8px; padding:5px 8px; border-radius:5px; background:${col}22; color:${col}; font-weight:700; text-align:center; font-size:12px;">
                🚦 ${estado}
            </div>
        </div>`;
    }

    // Actualiza el panel lateral con ranking de comunidades
    function _updateCommunityPanel(stats, metric) {
        const container = document.getElementById('map-community-rows');
        const infoEl = document.getElementById('map-sample-info');
        if (!container) return;

        const getValue = s => metric === 'positiva' ? s.pctPos :
                              metric === 'temor'    ? s.pctTemor : s.balance;
        const getColor = s => _getHeatColor(getValue(s), metric);
        const suffix = metric === 'balance' ? ' pp' : '%';

        // Ordenar: positiva/balance desc, temor asc
        let entries = Object.entries(stats).sort((a, b) =>
            metric === 'temor' ? a[1].pctTemor - b[1].pctTemor : getValue(b[1]) - getValue(a[1])
        );

        const totalN = Object.values(stats).reduce((a, s) => a + s.n, 0);
        if (infoEl) infoEl.textContent = `${entries.length} comunidades · n=${totalN}`;

        container.innerHTML = entries.map(([name, s]) => {
            const val = getValue(s);
            const col = getColor(s);
            const barPct = metric === 'balance' ? Math.max(0, val + 100) / 2 : Math.min(100, Math.max(0, val));
            return `
            <div style="background:rgba(255,255,255,0.04); border-radius:6px; padding:7px 9px; border-left:3px solid ${col};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
                    <span style="font-weight:600; color:var(--text); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:155px;" title="${name}">${name}</span>
                    <span style="font-weight:700; color:${col}; font-size:12px;">${val >= 0 ? (metric === 'balance' && val > 0 ? '+' : '') : ''}${val.toFixed(1)}${suffix}</span>
                </div>
                <div style="background:rgba(255,255,255,0.1); border-radius:4px; height:5px; overflow:hidden;">
                    <div style="width:${barPct}%; height:100%; background:${col}; border-radius:4px; transition:width 0.4s;"></div>
                </div>
                <div style="font-size:10px; color:var(--text-sec); margin-top:2px;">n=${s.n}</div>
            </div>`;
        }).join('');
    }

    // --- ALGORITMO CHOROPLETH DINÁMICO (HEAT MAP MEJORADO) ---
    function updateMapColors() {
        if (!leafletMap || dynamicLayers.length === 0) return;

        const stats = _computeMapStats();
        const statsNorm = {};
        for (const com in stats) statsNorm[_normGeo(com)] = { name: com, ...stats[com] };

        // Función para buscar match fuzzy
        const findStats = (featureName) => {
            const fn = _normGeo(featureName);
            if (statsNorm[fn]) return statsNorm[fn];
            for (const k in statsNorm) {
                if (k.length >= 3 && (fn.includes(k) || k.includes(fn))) {
                    return statsNorm[k];
                }
            }
            return null;
        };

        const getValue = (s) => currentMapMetric === 'positiva' ? s.pctPos :
                                 currentMapMetric === 'temor'    ? s.pctTemor : s.balance;

        dynamicLayers.forEach(layerObj => {
            layerObj.layer.eachLayer(featureLayer => {
                const props = featureLayer.feature.properties;
                const featureName = props._geoName || props.COM_DESC || props.BARLO_DESC ||
                    props.Localidad || props.Localidade || props.DISTRITO || props.DIST_DESC_ || props.BAR_LOC || '';

                const s = findStats(featureName);

                if (s) {
                    const val = getValue(s);
                    const col = _getHeatColor(val, currentMapMetric);
                    featureLayer.setStyle({ fillColor: col, color: col, fillOpacity: 0.65, weight: 1.5 });
                    featureLayer.bindPopup(_buildPopup(featureName || s.name, s, currentMapMetric));
                } else {
                    const dc = layerObj.defaultColor || '#ffffff';
                    featureLayer.setStyle({ fillColor: dc, color: dc, fillOpacity: 0.08, weight: 0.8 });
                    featureLayer.bindPopup(featureLayer.options.originalPopupText ||
                        `<b>${featureName || 'Área'}</b><br><i style="color:#888;">Sin datos suficientes (n<5)</i>`);
                }
            });
        });

        // Leyenda dinámica actualizada
        _updateMapLegend();

        // Actualizar panel lateral
        _updateCommunityPanel(stats, currentMapMetric);
    }

    function _updateMapLegend() {
        if (mapLegend) leafletMap.removeControl(mapLegend);
        mapLegend = L.control({ position: 'bottomleft' });
        mapLegend.onAdd = function () {
            let div = L.DomUtil.create('div', 'info legend');
            Object.assign(div.style, {
                background: 'var(--glass-bg)', backdropFilter: 'blur(10px)',
                padding: '12px 16px', border: '1px solid var(--glass-border)',
                borderRadius: '10px', color: 'var(--text)', fontSize: '12px',
                lineHeight: '2', boxShadow: '0 4px 8px rgba(0,0,0,0.4)', minWidth: '190px'
            });

            const labels = {
                positiva: ['🗺️ Percepción Positiva (NAUTA)',
                    ['#22c55e', 'Favorable (\u226570%)'],
                    ['#f59e0b', 'Atenci\u00f3n (50\u201370%)'],
                    ['#ef4444', 'Cr\u00edtico (<50%)']],
                temor: ['🗺️ Presencia de Temores',
                    ['#22c55e', 'Bajo (<15%)'],
                    ['#f59e0b', 'Moderado (15\u201330%)'],
                    ['#ef4444', 'Alto (\u226530%)']],
                balance: ['🗺️ Balance Neto (Pos\u2212Neg)',
                    ['#22c55e', 'Positivo (\u2265+20pp)'],
                    ['#f59e0b', 'Neutro (0\u201320pp)'],
                    ['#ef4444', 'Negativo (<0pp)']]
            };

            const [title, ...rows] = labels[currentMapMetric] || labels['positiva'];
            div.innerHTML = `<b style="font-size:13px;">${title}</b><br>` +
                rows.map(([color, text]) =>
                    `<i style="background:${color};width:14px;height:14px;display:inline-block;border-radius:3px;margin-right:7px;vertical-align:middle;"></i>${text}`
                ).join('<br>') +
                `<br><i style="background:rgba(255,255,255,0.12);border:1px solid #555;width:14px;height:14px;display:inline-block;border-radius:3px;margin-right:7px;vertical-align:middle;"></i>Sin datos suficientes`;
            return div;
        };
        mapLegend.addTo(leafletMap);
    }
});

