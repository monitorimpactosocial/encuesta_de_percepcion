// ESTADO GLOBAL
let currentData = [];
let charts = {};
let leafletMap = null; // Instancia global del mapa de Leaflet
let mapLayers = {}; // Capas del mapa
let dynamicLayers = []; // Capas sujetas a repintado de mapa de calor
let mapLegend = null; // Control de leyenda del mapa

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
const colEstudios = 'estudios';
const colIngresos = 'podría indicarnos en qué rango se encuentra sus ingresos económicos familiaresesto quiere decir la suma de lo que ganan todas las personas que trabajan en la casa';

// CONSTANTES Y COLORES DE GRÁFICOS
const yearColors = {
    '2022': { bg: 'rgba(0, 240, 255, 0.75)', border: 'rgba(0, 240, 255, 1)' }, // Cyan Neon
    '2023': { bg: 'rgba(255, 0, 128, 0.75)', border: 'rgba(255, 0, 128, 1)' }, // Magenta Neon
    '2024': { bg: 'rgba(144, 255, 0, 0.75)', border: 'rgba(144, 255, 0, 1)' }, // Lime Neon
    '2025': { bg: 'rgba(255, 165, 0, 0.75)', border: 'rgba(255, 140, 0, 1)' }  // Orange Neon
};
const defaultColor = { bg: 'rgba(0, 240, 255, 0.75)', border: 'rgba(0, 240, 255, 1)' };

// INICIALIZACIÓN
document.addEventListener("DOMContentLoaded", () => {

    // LOGIN STATE
    const btnLogin = document.getElementById('btn-login');
    const inputUser = document.getElementById('username');
    const inputPass = document.getElementById('password');
    const loginError = document.getElementById('login-error');

    if (localStorage.getItem("paracel_logged") === "true") {
        showDashboard();
    } else {
        inputUser.focus();
    }

    btnLogin.addEventListener('click', () => {
        if (inputUser.value === "user" && inputPass.value === "123") {
            localStorage.setItem("paracel_logged", "true");
            loginError.style.display = "none";
            showDashboard();
        } else {
            loginError.style.display = "block";
        }
    });

    inputPass.addEventListener("keypress", (e) => {
        if (e.key === "Enter") btnLogin.click();
    });

    document.getElementById('btn-logout').addEventListener('click', () => {
        localStorage.removeItem("paracel_logged");
        location.reload();
    });

    document.getElementById('btn-reset').addEventListener('click', () => {
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
                    updateDashboard();
                }
            }, 50);
        });
    });

    // FUNCIONES PRINCIPALES
    function showDashboard() {
        document.getElementById('login-screen').style.display = "none";
        document.getElementById('dashboard-screen').style.display = "flex";

        // Pre-procesar columna de percepcion
        encuestasData.forEach(d => {
            let keys = Object.keys(d);
            let posKey = keys.find(k => k.toLowerCase().includes('positivo'));
            let negKey = keys.find(k => k.toLowerCase().includes('temor'));

            let negResp = String(posKey ? d[posKey] : '').trim().toLowerCase();
            // Si "no vi algun aspecto..." está vacío/nulo, significa que SÍ ve aspectos positivos.
            let isPositiva = !(negResp.includes('no vi') || negResp.includes('ns') || negResp.includes('nr') || negResp === 'true');

            // Si dijo algo negativo en "positivas" o es neutro, revisamos "temores"
            let probResp = String(negKey ? d[negKey] : '').trim().toLowerCase();
            let isNegativa = !isPositiva && (probResp !== '' && probResp !== 'nan' && probResp !== 'ninguno' && probResp !== 'ninguna' && !probResp.includes('ns') && !probResp.includes('nr') && probResp !== 'false');

            if (isPositiva) d['percepción_clasificada'] = 'Positiva';
            else if (isNegativa) d['percepción_clasificada'] = 'Negativa';
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
            const btn = document.createElement("button");
            btn.className = "filter-btn";
            btn.dataset.col = colName;
            btn.dataset.val = String(val);
            btn.innerText = String(val).charAt(0).toUpperCase() + String(val).slice(1);

            // Evento click (Single select vs Múltiple / Toggle con CTRL)
            btn.addEventListener('click', (e) => {
                const isMultiSelect = e.ctrlKey || e.metaKey;
                const vStr = String(val);

                if (!isMultiSelect) {
                    // Si NO apretó CTRL, Limpiar todos los botones de este grupo y dejar solo este
                    activeFilters[colName].clear();
                    container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    activeFilters[colName].add(vStr);
                    btn.classList.add('active');
                } else {
                    // Si SÍ apretó CTRL, comportamiento Toggle
                    if (activeFilters[colName].has(vStr)) {
                        activeFilters[colName].delete(vStr);
                        btn.classList.remove('active');
                    } else {
                        activeFilters[colName].add(vStr);
                        btn.classList.add('active');
                    }
                }
                updateDashboard();
            });

            container.appendChild(btn);
        });
    }

    // Boton Exportar PNG
    document.getElementById('btn-export').addEventListener('click', () => {
        const activeTab = document.querySelector('.tab-content.active');
        if (!activeTab) return;
        const canvases = activeTab.querySelectorAll('canvas');
        canvases.forEach((canvas, idx) => {
            let link = document.createElement('a');
            link.download = `grafico_paracel_${idx + 1}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        });
    });

    // Boton Theme Toggle
    const themeBtn = document.getElementById('btn-theme');
    document.documentElement.setAttribute('data-theme', 'dark'); // Fondo oscuro por default
    themeBtn.innerText = '☀️ Light';

    themeBtn.addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
            document.documentElement.removeAttribute('data-theme');
            themeBtn.innerText = '🌙 Dark';
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeBtn.innerText = '☀️ Light';
        }
        updateDashboard(); // Redibujar todos los graficos con colores correctos
    });

    // APLICAR FILTROS Y RECOMPUTAR GRAFICOS
    function updateDashboard() {
        let filtered = encuestasData;

        // Comprobar cada dimensión si tiene algún filtro activo (OR dentro de la dimensión, AND entre dimensiones)
        for (const [colName, selectedSet] of Object.entries(activeFilters)) {
            if (selectedSet.size > 0) {
                // Validación Case Insensitive permitiendo match exacto con el Dataset o con el valor capitalizado del Boton
                filtered = filtered.filter(d =>
                    selectedSet.has(String(d[colName]).toLowerCase()) ||
                    selectedSet.has(String(d[colName]))
                );
            }
        }

        currentData = filtered;
        document.getElementById('total-encuestas').innerText = `Total Encuestas: ${currentData.length}`;

        // RENDER MODULE 1
        renderKPIs(currentData);
        renderSingleColumnChart('chartComunidades', 'bar', 'comunidad');
        renderMultiColumnChart('chartPositivos', 'bar', 'Aspectos Positivos (%)', configAspectosPositivos);
        renderMultiColumnChart('chartNegativos', 'bar', 'Problemas / Negativos (%)', configAspectosNegativos);

        // RENDER MODULE 2
        renderMultiColumnChart('chartExpectativas', 'bar', 'Expectativas (%)', configExpectativas);
        renderMultiColumnChart('chartMedios', 'bar', 'Medios de Info. (%)', configMedios); // Cambiado a barras
        renderSingleColumnChart('chartTemores', 'bar', colTemores); // Convertido a barras permanentemente

        // RENDER MODULE 3
        renderSingleColumnChart('chartEstudios', 'bar', colEstudios);
        renderSingleColumnChart('chartIngresos', 'bar', colIngresos);
        renderMultiColumnChart('chartTrabajo', 'bar', 'Situación Laboral (%)', configOcupacion);

        // RENDER MODULE 4 (EVOLUCION CLAVE 2022-2025)
        renderEvolPositiva();
        renderMultiColumnChart('chartEvolFaltaLaboral', 'bar', 'Falta Oferta Laboral (%)', ['poca oferta laboral']);
        renderMultiColumnChart('chartEvolAtributos', 'bar', 'Atributos (%)', ['tranquilidad', 'la gente']);
        renderEvolProduccion();
        renderMultiColumnChart('chartEvolBeneficios', 'line', 'Beneficios (%)', ['puestos de trabajo para', 'caminos o rutas en zonas']);
        renderMultiColumnChart('chartEvolCanales', 'bar', 'Canales (%)', configMedios);

        // RENDER MODULE 5 (TABLA DE DATOS)
        renderDataTable(currentData);

        // RENDER MODULE 6 (MAPA GIS)
        if (leafletMap) {
            updateMapColors();
        }
    }

    // DINAMICA DE KPIS HEADER
    function renderKPIs(data) {
        if (!data || data.length === 0) {
            document.getElementById('kpi-total').innerText = '0';
            document.getElementById('kpi-positiva').innerText = '0%';
            document.getElementById('kpi-problema').innerText = '-';
            document.getElementById('kpi-atributo').innerText = '-';
            return;
        }

        // 1. Total Encuestas
        document.getElementById('kpi-total').innerText = data.length;

        // 2. Percepcion Positiva
        let countPos = data.filter(d => d['percepción_clasificada'] === 'Positiva').length;
        document.getElementById('kpi-positiva').innerText = ((countPos / data.length) * 100).toFixed(1) + '%';

        // Helper buscar llaves flex (mayus/minus)
        function getFuzzyKey(obj, substring) {
            return Object.keys(obj).find(k => k.toLowerCase().includes(substring.toLowerCase())) || substring;
        }

        // 3. Top Problema
        let problemas = {};
        data.forEach(d => {
            configAspectosNegativos.forEach(p => {
                let actual = getFuzzyKey(d, p);
                let v = d[actual];
                let strV = String(v).trim().toLowerCase();
                if (strV !== "undefined" && strV !== "null" && strV !== "" && strV !== "ninguno" && strV !== "nan" && strV !== "false" && strV !== "-") {
                    problemas[p] = (problemas[p] || 0) + 1;
                }
            });
        });
        let topProblema = Object.keys(problemas).sort((a, b) => problemas[b] - problemas[a])[0];
        document.getElementById('kpi-problema').innerText = topProblema ? truncate(topProblema, 25) : 'N/A';

        // 4. Top Atributo
        let atributos = {};
        data.forEach(d => {
            configAspectosPositivos.forEach(a => {
                let actual = getFuzzyKey(d, a);
                let v = d[actual];
                let strV = String(v).trim().toLowerCase();
                if (strV !== "undefined" && strV !== "null" && strV !== "" && strV !== "ninguno" && strV !== "nan" && strV !== "false" && strV !== "-") {
                    atributos[a] = (atributos[a] || 0) + 1;
                }
            });
        });
        let topAtributo = Object.keys(atributos).sort((a, b) => atributos[b] - atributos[a])[0];
        document.getElementById('kpi-atributo').innerText = topAtributo ? truncate(topAtributo, 25) : 'N/A';
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

                let count = yearData.filter(d => {
                    let v = d[actualKey];
                    if (v === null || v === undefined) return false;
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

        let datasets = [];
        let dataPoints = [];

        years.forEach(year => {
            let yearData = currentData.filter(d => String(d['año']) === year);
            const total = yearData.length;

            // Calculamos gente que reporto algun aspecto positivo (no marco "No vio algun aspecto positivo aun")
            let posKey = Object.keys(yearData[0] || {}).find(k => k.toLowerCase().includes('positivo'));

            let countPositive = yearData.filter(d => {
                let negResp = String(posKey ? d[posKey] : '').trim().toLowerCase();
                return !(negResp.includes('no vi') || negResp.includes('ns') || negResp.includes('nr') || negResp === 'true');
            }).length;

            let pct = total > 0 ? ((countPositive / total) * 100).toFixed(1) : 0;
            dataPoints.push(pct);
        });

        datasets.push({
            label: 'Percepción Positiva (%)',
            data: dataPoints,
            backgroundColor: 'rgba(2, 132, 199, 0.1)',
            borderColor: '#0284c7', // Paracel blue
            borderWidth: 2,
            fill: true,
            tension: 0.3
        });

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

        const blob = new Blob(["\ufeff", csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `Data_Percepcion_Paracel_${new Date().getTime()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // --- MÓDULO GIS LEAFLET ---
    function initLeafletMap() {
        if (leafletMap) {
            leafletMap.invalidateSize(); // Refresco si ya existe
            return;
        }

        // Crear mapa base centrado en Concepcion
        leafletMap = L.map('map-container').setView([-23.4, -57.4], 8);

        // Capa satelital de fondo (Esri World Imagery)
        const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri'
        }).addTo(leafletMap);

        // Capa callejera oscura de fondo (CartoDB DarkMatter)
        const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap & CartoDB'
        });

        // Estilos para GeoJSON
        const stylePropiedades = { color: "#90ff00", weight: 2, fillColor: "#90ff00", fillOpacity: 0.2 }; // Lime
        const styleIndigenas = { color: "#ff007f", weight: 2, fillColor: "#ff007f", fillOpacity: 0.4 };   // Magenta
        const styleComunidades = { color: "#00f0ff", weight: 2, fillColor: "#00f0ff", fillOpacity: 0.3 }; // Cyan
        const styleDistritos = { color: "#ffffff", weight: 1, fillOpacity: 0.05, dashArray: '5, 5' };     // Blanco DASH

        mapLayers = {};
        let basemaps = { "Satélite (Esri)": satelliteLayer, "Calles Oscuro (CartoDB)": darkLayer };
        let overlays = {};

        dynamicLayers = []; // Reset capas dinamicas

        // Validamos existencia de mapasData inyectado por script externo
        if (typeof mapasData !== 'undefined') {

            // 1. Distritos (Paracel)
            if (mapasData['distritos_paracel']) {
                let layer = L.geoJSON(mapasData['distritos_paracel'], {
                    style: styleDistritos,
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Distrito:</b> ${feature.properties.DISTRITO || feature.properties.DIST_DESC_ || 'N/A'}`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(leafletMap);
                mapLayers['Distritos'] = layer;
                overlays['Límites Distritales'] = layer;
                dynamicLayers.push({ layer: layer, defaultColor: '#ffffff' });
            }

            // 2. Propiedades Forestales
            if (mapasData['propiedades_forestales']) {
                let layer = L.geoJSON(mapasData['propiedades_forestales'], {
                    style: stylePropiedades,
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Estancia:</b> ${feature.properties.Estancia || 'N/A'} <br/> <b>Área:</b> ${feature.properties.Area || 'N/A'} Ha`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(leafletMap);
                mapLayers['Forestales'] = layer;
                overlays['Núcleos Forestales PARACEL'] = layer;
            }

            // 3. Componentes Industriales
            if (mapasData['componentes_industriales']) {
                let layer = L.geoJSON(mapasData['componentes_industriales'], {
                    style: { color: "#ffea00", weight: 3, fillColor: "#ffea00", fillOpacity: 0.6 },
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Instalación:</b> ${feature.properties.proyecto || feature.properties.Name || 'Componente Industrial'}`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(leafletMap);
                mapLayers['Industria'] = layer;
                overlays['Planta Industrial y Puertos'] = layer;
            }

            // 4. Comunidades Indígenas
            if (mapasData['comunidades_indigenas']) {
                let layer = L.geoJSON(mapasData['comunidades_indigenas'], {
                    style: styleIndigenas,
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Comunidad Indígena:</b> ${feature.properties.COM_DESC || feature.properties.BARLO_DESC || 'N/A'}`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(leafletMap);
                mapLayers['Indigenas'] = layer;
                overlays['Comunidades Indígenas'] = layer;
                dynamicLayers.push({ layer: layer, defaultColor: '#ff007f' });
            }

            // 5. Comunidades Rurales (Industrial + Forestal)
            let comunidadesLayer = L.layerGroup().addTo(leafletMap);
            if (mapasData['comunidades_industriales']) {
                let indLayer = L.geoJSON(mapasData['comunidades_industriales'], {
                    style: styleComunidades,
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Comunidad (Z. Ind.):</b> ${feature.properties.Localidade || 'N/A'}`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(comunidadesLayer);
                dynamicLayers.push({ layer: indLayer, defaultColor: '#00f0ff' });
            }
            if (mapasData['comunidades_forestales']) {
                let forLayer = L.geoJSON(mapasData['comunidades_forestales'], {
                    style: styleComunidades,
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Comunidad (Z. For.):</b> ${feature.properties.Localidad || 'N/A'}`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(comunidadesLayer);
                dynamicLayers.push({ layer: forLayer, defaultColor: '#00f0ff' });
            }
            overlays['Comunidades de Influencia Formal'] = comunidadesLayer;

            // 6. Barrios Concepción y Amambay
            let barriosLayer = L.layerGroup();
            if (mapasData['barrios_concepcion']) {
                let layerC = L.geoJSON(mapasData['barrios_concepcion'], {
                    style: { color: "#ffffff", weight: 0.5, fillColor: "#ffffff", fillOpacity: 0.1 },
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Barrio (Concepción):</b> ${feature.properties.BARLO_DESC || feature.properties.BARRIO || feature.properties.BAR_LOC || 'N/A'}`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(barriosLayer);
                dynamicLayers.push({ layer: layerC, defaultColor: '#ffffff' });
            }
            if (mapasData['barrios_amambay']) {
                let layerA = L.geoJSON(mapasData['barrios_amambay'], {
                    style: { color: "#ffffff", weight: 0.5, fillColor: "#ffffff", fillOpacity: 0.1 },
                    onEachFeature: function (feature, layer) {
                        let txt = `<b>Barrio (Amambay):</b> ${feature.properties.BARLO_DESC || feature.properties.BARRIO || feature.properties.BAR_LOC || 'N/A'}`;
                        layer.options.originalPopupText = txt;
                        layer.bindPopup(txt);
                    }
                }).addTo(barriosLayer);
                dynamicLayers.push({ layer: layerA, defaultColor: '#ffffff' });
            }
            overlays['Capa Urbana / Barrios Centrales'] = barriosLayer;

        } else {
            console.error("No se detectó la variable mapasData. Revisa si procesar_mapas.py corrió y si mapas_data.js está enlazado correctamente.");
        }

        // Agregar control de capas a la vista TopRight
        L.control.layers(basemaps, overlays, { collapsed: false }).addTo(leafletMap);
        leafletMap.invalidateSize(); // Forzamos recuadro correcto

        // Disparar coloración inicial
        updateMapColors();
    }

    // --- ALGORITMO CHOROPLETH DINÁMICO ---
    function updateMapColors() {
        if (!leafletMap || dynamicLayers.length === 0) return;

        // 1. Calcular Percepción por Comunidad / Área
        let stats = {};

        currentData.forEach(d => {
            let com = String(d['comunidad'] || d['distrito'] || d['barrio'] || '').trim().toLowerCase();
            if (!com || com === 'nan' || com === '-') return;

            if (!stats[com]) stats[com] = { total: 0, pos: 0 };
            stats[com].total++;
            if (d['percepción_clasificada'] === 'Positiva') {
                stats[com].pos++;
            }
        });

        // Convertir a porcentajes
        let perceptMap = {};
        for (let c in stats) {
            perceptMap[c] = (stats[c].pos / stats[c].total) * 100;
        }

        // Helper para normalizar nombres y cruzar GIS con Excel (Fuzzy Matcher básico)
        function normalizeName(name) {
            if (!name) return "";
            return String(name).toLowerCase()
                .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // quita acentos
                .replace(/[^a-z0-9]/g, ""); // quita espacios y caracteres raros
        }

        let perceptMapNorm = {};
        for (let c in perceptMap) {
            perceptMapNorm[normalizeName(c)] = perceptMap[c];
        }

        // 2. Colorear capas
        function getColorForPct(pct) {
            if (pct >= 60) return '#00ff73'; // Verde - Alta Aceptacion
            if (pct >= 40) return '#ffea00'; // Amarillo - Neutra / Riesgo
            return '#ff007f'; // Rojo - Tension / Negatividad
        }

        dynamicLayers.forEach(layerObj => {
            layerObj.layer.eachLayer(function (featureLayer) {
                let props = featureLayer.feature.properties;
                let featureName = props.COM_DESC || props.BARLO_DESC || props.Localidad || props.Localidade || props.DISTRITO || props.DIST_DESC_ || props.BAR_LOC || props.Comunidad || "";

                let normFeatureName = normalizeName(featureName);

                let matchedPct = null;
                // Match directo
                if (perceptMapNorm[normFeatureName] !== undefined) {
                    matchedPct = perceptMapNorm[normFeatureName];
                } else {
                    // Match parcial
                    for (let k in perceptMapNorm) {
                        if (normFeatureName.includes(k) || k.includes(normFeatureName)) {
                            if (k !== "" && normFeatureName !== "") {
                                matchedPct = perceptMapNorm[k];
                                break;
                            }
                        }
                    }
                }

                // Aplicar estilo cruzado
                if (matchedPct !== null) {
                    let c = getColorForPct(matchedPct);
                    featureLayer.setStyle({ fillColor: c, color: c, fillOpacity: 0.6, weight: 2 });
                    let originalPopup = featureLayer.options.originalPopupText || `<b>Área:</b> ${featureName}`;
                    featureLayer.bindPopup(`${originalPopup}<br><hr style="margin:5px 0; border:rgba(0,0,0,0.1)"><b style="color:${c}; font-size:14px;">Percepción Positiva: ${matchedPct.toFixed(1)}%</b>`);
                } else {
                    // Reset a color nativo o nulo
                    let defaultColor = layerObj.defaultColor || '#ffffff';
                    featureLayer.setStyle({ fillColor: defaultColor, color: defaultColor, fillOpacity: 0.1, weight: 1 });
                    featureLayer.bindPopup(featureLayer.options.originalPopupText || `<b>Área:</b> ${featureName}`);
                }
            });
        });

        // 3. Actualizar Leyenda Flotante
        if (mapLegend) {
            leafletMap.removeControl(mapLegend);
        }

        mapLegend = L.control({ position: 'bottomleft' });
        mapLegend.onAdd = function (map) {
            let div = L.DomUtil.create('div', 'info legend');
            div.style.background = 'var(--glass-bg)';
            div.style.backdropFilter = 'blur(10px)';
            div.style.padding = '12px 18px';
            div.style.border = '1px solid var(--glass-border)';
            div.style.borderRadius = '8px';
            div.style.color = 'var(--text)';
            div.style.fontSize = '12px';
            div.style.lineHeight = '2';
            div.style.boxShadow = '0 4px 6px rgba(0,0,0,0.3)';

            div.innerHTML += '<b style="font-size:14px">🗺️ Mapa de Calor (Percepción)</b><br>';
            div.innerHTML += '<i style="background:#00ff73; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:8px; vertical-align:middle;"></i> Positiva (>60%)<br>';
            div.innerHTML += '<i style="background:#ffea00; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:8px; vertical-align:middle;"></i> Neutra (40-60%)<br>';
            div.innerHTML += '<i style="background:#ff007f; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:8px; vertical-align:middle;"></i> Negativa (<40%)<br>';
            div.innerHTML += '<i style="background:#ffffff; opacity:0.3; border:1px solid #444; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:8px; vertical-align:middle;"></i> Sin datos suficientes';
            return div;
        };
        mapLegend.addTo(leafletMap);
    }
});
