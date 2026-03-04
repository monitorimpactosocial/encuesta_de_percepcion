// ESTADO GLOBAL
let currentData = [];
let charts = {};

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
                updateDashboard();
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

});
