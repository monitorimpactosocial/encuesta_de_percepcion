// ESTADO GLOBAL
let currentData = [];
let charts = {};

// ESTADOS DE FILTROS (Múltiples selecciones permitidas por categoría)
let activeFilters = {
    'Año': new Set(),
    'Género': new Set(),
    'Edad (Rango)': new Set(),
    'NSE_FINAL': new Set(),
    'Comunidad ': new Set()
};

// CONFIGURACIÓN CHART.JS GLOBALES
Chart.defaults.color = '#8b949e';
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
        activeFilters = { 'Año': new Set(), 'Género': new Set(), 'Edad (Rango)': new Set(), 'NSE_FINAL': new Set(), 'Comunidad ': new Set() };
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
        });
    });

    // FUNCIONES PRINCIPALES
    function showDashboard() {
        document.getElementById('login-screen').style.display = "none";
        document.getElementById('dashboard-screen').style.display = "flex";

        // Crear botones de filtros
        createFilterButtons('filter-anio', 'Año');
        createFilterButtons('filter-genero', 'Género');
        createFilterButtons('filter-edad', 'Edad (Rango)');
        createFilterButtons('filter-nse', 'NSE_FINAL');
        createFilterButtons('filter-comunidad', 'Comunidad ');

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

            // Evento click (Toggle / Multiple)
            btn.addEventListener('click', () => {
                if (activeFilters[colName].has(String(val))) {
                    activeFilters[colName].delete(String(val));
                    btn.classList.remove('active');
                } else {
                    activeFilters[colName].add(String(val));
                    btn.classList.add('active');
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
        renderMultiColumnChart('chartMedios', 'line', 'Medios de Info. (%)', configMedios);
        renderSingleColumnChart('chartTemores', 'pie', colTemores);

        // RENDER MODULE 3
        renderSingleColumnChart('chartEstudios', 'bar', colEstudios);
        renderSingleColumnChart('chartIngresos', 'bar', colIngresos);
        renderMultiColumnChart('chartTrabajo', 'bar', 'Situación Laboral (%)', configOcupacion);
    }

    // ----------------------------------------------------
    // HELPERS DE GRAFICACIÓN CHART.JS POR AÑO (SERIES)
    // ----------------------------------------------------

    const yearColors = {
        '2022': { bg: 'rgba(0, 240, 255, 0.75)', border: 'rgba(0, 240, 255, 1)' }, // Cyan Neon
        '2023': { bg: 'rgba(255, 0, 128, 0.75)', border: 'rgba(255, 0, 128, 1)' }, // Magenta Neon
        '2024': { bg: 'rgba(144, 255, 0, 0.75)', border: 'rgba(144, 255, 0, 1)' }  // Lime Neon
    };
    const defaultColor = { bg: 'rgba(0, 240, 255, 0.75)', border: 'rgba(0, 240, 255, 1)' };

    // Para contar presencias ("Sí") cruzando múltiples columnas
    function renderMultiColumnChart(canvasId, type, label, keysToCount) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (charts[canvasId]) charts[canvasId].destroy();

        let years = Array.from(activeFilters['Año']);
        if (years.length === 0) {
            years = [...new Set(currentData.map(d => String(d['Año'])))].filter(y => y !== 'undefined' && y !== 'null' && y !== 'NaN').sort();
        }

        let labels = keysToCount.map(k => truncate(k));
        let datasets = [];

        years.forEach(year => {
            let yearData = currentData.filter(d => String(d['Año']) === year);
            const total = yearData.length;
            let dataPoints = [];

            keysToCount.forEach(key => {
                let count = yearData.filter(d => {
                    let v = d[key];
                    if (v === null || v === undefined) return false;
                    if (typeof v === 'number' && isNaN(v)) return false;
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

        let years = Array.from(activeFilters['Año']);
        if (years.length === 0) {
            years = [...new Set(currentData.map(d => String(d['Año'])))].filter(y => y !== 'undefined' && y !== 'null' && y !== 'NaN').sort();
        }

        // Obtener respuestas válidas históricamente
        let allValidAnswers = new Set();
        let globalCounts = {};
        currentData.forEach(d => {
            let v = d[colName];
            if (v === null || v === undefined) return;
            if (typeof v === 'number' && isNaN(v)) return;
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
            let yearData = currentData.filter(d => String(d['Año']) === year);
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
