// ESTADO GLOBAL
let currentData = [];
let charts = {};

// ESTADOS DE FILTROS (Múltiples selecciones permitidas por categoría)
let activeFilters = {
    'es_panel': new Set(),
    'año': new Set(),
    'género': new Set(),
    'edad': new Set(),
    'nse': new Set(),
    'comunidad': new Set()
};

// CONFIGURACIÓN CHART.JS GLOBALES
Chart.defaults.color = '#e2e8f0'; // Color de fuente más visible
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
const colEstudios = 'podría indicarnos cuál es su nivel de estudios';
const colIngresos = 'podría indicarnos en qué rango se encuentra sus ingresos económicos familiaresesto quiere decir la suma de lo que ganan todas las personas que trabajan en la casa';

// CONSTANTES Y COLORES DE GRÁFICOS
const yearColors = {
    '2022': { bg: 'rgba(0, 240, 255, 0.75)', border: 'rgba(0, 240, 255, 1)' }, // Cyan Neon
    '2023': { bg: 'rgba(255, 0, 128, 0.75)', border: 'rgba(255, 0, 128, 1)' }, // Magenta Neon
    '2024': { bg: 'rgba(144, 255, 0, 0.75)', border: 'rgba(144, 255, 0, 1)' }  // Lime Neon
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
        activeFilters = { 'es_panel': new Set(), 'año': new Set(), 'género': new Set(), 'edad': new Set(), 'nse': new Set(), 'comunidad': new Set() };
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

            // Redibujar gráficos para solucionar bug de canvas 0x0 en divs ocultos
            updateDashboard();
        });
    });

    // FUNCIONES PRINCIPALES
    function showDashboard() {
        document.getElementById('login-screen').style.display = "none";
        document.getElementById('dashboard-screen').style.display = "flex";

        // Crear botones de filtros
        createFilterButtons('filter-muestra', 'es_panel');
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

        // Extraer valores únicos válidos
        const uniqueValues = [...new Set(encuestasData.map(d => d[colName]))]
            .filter(v => v !== null && v !== undefined && v !== "" && String(v).toLowerCase() !== "nan" && String(v).toLowerCase() !== "ninguno/a")
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

    // APLICAR FILTROS Y RECOMPUTAR GRAFICOS
    function updateDashboard() {
        let filtered = encuestasData;

        // Comprobar cada dimensión si tiene algún filtro activo (OR dentro de la dimensión, AND entre dimensiones)
        for (const [colName, selectedSet] of Object.entries(activeFilters)) {
            if (selectedSet.size > 0) {
                filtered = filtered.filter(d => selectedSet.has(String(d[colName])));
            }
        }

        currentData = filtered;
        document.getElementById('total-encuestas').innerText = `Total Encuestas: ${currentData.length}`;

        // RENDER MODULE 1
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

        // RENDER MODULE 4 (PANEL EXCLUSIVE)
        renderMultiColumnChart('chartPanelPositivos', 'line', 'Evol. Panel Positivos', configAspectosPositivos);
        renderMultiColumnChart('chartPanelExpectativas', 'line', 'Evol. Panel Expectativas', configExpectativas);
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

            keysToCount.forEach(key => {
                let count = yearData.filter(d => {
                    let v = d[key];
                    if (v === null || v === undefined) return false;
                    // Ya NO filtramos con isNaN genérico porque 'v' puede ser texto como "Oferta laboral"
                    let strV = String(v).trim().toLowerCase();
                    if (strV === "" || strV === "-" || strV === "nan" || strV === "ninguno" || strV === "ninguna") return false;
                    return true;
                }).length;

                let pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                dataPoints.push(pct);
            });

            let colorObj = yearColors[year] || defaultColor;

            datasets.push({
                label: `${label} - ${year}`,
                data: dataPoints,
                backgroundColor: type === 'line' ? colorObj.bg.replace('0.7', '0.1') : colorObj.bg,
                borderColor: colorObj.border,
                borderWidth: 1,
                fill: type === 'line',
                tension: 0.3
            });
        });

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
            const total = yearData.length;

            let counts = {};
            yearData.forEach(d => {
                let strV = String(d[colName]).trim();
                counts[strV] = (counts[strV] || 0) + 1;
            });

            let dataPoints = [];
            validAnswersArray.forEach(ans => {
                let count = counts[ans] || 0;
                let pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                dataPoints.push(pct);
            });

            let colorObj = yearColors[year] || defaultColor;

            // Paleta para pie simple y vibrante
            const pieBgColors = ['#00f0ff', '#ff007f', '#90ff00', '#ffea00', '#9d00ff', '#ff5e00', '#00ff73', '#00b8ff'];

            datasets.push({
                label: `Distribución - ${year}`,
                data: dataPoints,
                backgroundColor: type === 'pie' ? pieBgColors : colorObj.bg,
                borderColor: type === 'pie' ? '#0d1117' : colorObj.border,
                borderWidth: type === 'pie' ? 2 : 1,
                fill: false
            });
        });

        drawChart(ctx, canvasId, type, labels, datasets);
    }

    // Motor de pintado genérico
    function drawChart(ctx, canvasId, type, labels, datasets) {
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
                        labels: { color: '#f0f6fc', font: { size: 11 } }
                    },
                    datalabels: {
                        color: type === 'pie' ? '#fff' : '#f0f6fc',
                        anchor: type === 'pie' ? 'center' : 'end',
                        align: type === 'pie' ? 'center' : (type === 'line' ? 'top' : 'end'),
                        formatter: function (value) { return value > 0 ? value + '%' : ''; },
                        font: { weight: 'bold', size: 9 },
                        display: function (context) {
                            return context.dataset.data[context.dataIndex] > 0; // Ocultar labels de 0%
                        }
                    }
                },
                scales: (type === 'bar' || type === 'line') ? {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#8b949e', font: { size: 11 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#8b949e', font: { size: 11 } }
                    }
                } : {}
            }
        });
    }

    function truncate(str) {
        let s = String(str).charAt(0).toUpperCase() + String(str).slice(1);
        if (s.length > 30) return s.substring(0, 30) + '...';
        return s;
    }

});
