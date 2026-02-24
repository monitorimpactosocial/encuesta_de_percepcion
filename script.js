// ESTADO GLOBAL
let currentData = [];
let charts = {};

// CONFIGURACIÓN CHART.JS GLOBALES
Chart.defaults.color = '#8b949e';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.register(ChartDataLabels);

// ARRAYS DE VARIABLES A GRAFICAR
const configAspectosPositivos = ['tranquilidad', 'seguridad', 'la gente', 'oferta laboral', 'desarrollo del sector comercial y servicios'];
const configAspectosNegativos = ['inseguridad', 'consumo de drogas', 'poca oferta laboral'];
const configExpectativas = ['más puestos de trabajo para personas de la zona', 'mejoras o nuevos caminos o rutas en zonas aledañas', 'nuevos comercios alrededor de la planta', 'formación laboral profesional de personas'];
const configMedios = ['radio', 'tv', 'redes sociales', 'medios de prensa', 'amigos conocidos'];

// INICIALIZACIÓN
document.addEventListener("DOMContentLoaded", () => {
    // Referencias DOM
    const btnLogin = document.getElementById('btn-login');
    const btnLogout = document.getElementById('btn-logout');
    const loginError = document.getElementById('login-error');
    const inputUser = document.getElementById('username');
    const inputPass = document.getElementById('password');

    const filterAnio = document.getElementById('filter-anio');
    const filterGenero = document.getElementById('filter-genero');
    const filterEdad = document.getElementById('filter-edad');
    const filterNse = document.getElementById('filter-nse');
    const filterSector = document.getElementById('filter-sector');
    const filterComunidad = document.getElementById('filter-comunidad');
    const btnReset = document.getElementById('btn-reset');

    // CHEQUEAR SESIÓN AL CARGAR
    if (localStorage.getItem("paracel_logged") === "true") {
        showDashboard();
    } else {
        inputUser.focus();
    }

    // EVENTOS DE LOGIN
    btnLogin.addEventListener('click', () => {
        if (inputUser.value === "user" && inputPass.value === "123") {
            localStorage.setItem("paracel_logged", "true");
            loginError.style.display = "none";
            showDashboard();
        } else {
            loginError.style.display = "block";
        }
    });

    inputPass.addEventListener("keypress", function (event) {
        if (event.key === "Enter") btnLogin.click();
    });

    btnLogout.addEventListener('click', () => {
        localStorage.removeItem("paracel_logged");
        location.reload();
    });

    // EVENTOS DE FILTROS
    const allFilters = [filterAnio, filterGenero, filterEdad, filterNse, filterSector, filterComunidad];
    allFilters.forEach(f => {
        f.addEventListener('change', updateDashboard);
    });

    btnReset.addEventListener('click', () => {
        allFilters.forEach(f => f.value = 'all');
        updateDashboard();
    });

    // FUNCIONES PRINCIPALES
    function showDashboard() {
        document.getElementById('login-screen').style.display = "none";
        document.getElementById('dashboard-screen').style.display = "flex";

        // Inicializar filtros con los datos crudos (encuestasData de data.js)
        populateFilter(filterGenero, 'género');
        populateFilter(filterEdad, 'edad');
        populateFilter(filterNse, 'nse');
        populateFilter(filterSector, 'sector');
        populateFilter(filterComunidad, 'comunidad');

        // Primer render
        updateDashboard();
    }

    // EXTRAE VALORES UNICOS PARA LLENAR LOS SELECTS
    function populateFilter(selectElement, colName) {
        const uniqueValues = [...new Set(encuestasData.map(d => d[colName]))]
            .filter(v => v !== null && v !== undefined && v !== "" && v !== "Ninguno/a")
            .sort();

        uniqueValues.forEach(val => {
            let option = document.createElement("option");
            option.value = val;
            option.text = String(val).charAt(0).toUpperCase() + String(val).slice(1);
            selectElement.appendChild(option);
        });
    }

    // FILTRADO DINÁMICO CADA VEZ QUE CAMBIA UN SELECT
    function updateDashboard() {
        let filtered = encuestasData;

        // Recuperar valores del DOM
        const valAnio = filterAnio.value;
        const valGenero = filterGenero.value;
        const valEdad = filterEdad.value;
        const valNse = filterNse.value;
        const valSector = filterSector.value;
        const valComunidad = filterComunidad.value;

        // Filtrar paso a paso
        if (valAnio !== 'all') filtered = filtered.filter(d => String(d['año']) === valAnio);
        if (valGenero !== 'all') filtered = filtered.filter(d => String(d['género']) === valGenero);
        if (valEdad !== 'all') filtered = filtered.filter(d => String(d['edad']) === valEdad);
        if (valNse !== 'all') filtered = filtered.filter(d => String(d['nse']) === valNse);
        if (valSector !== 'all') filtered = filtered.filter(d => String(d['sector']) === valSector);
        if (valComunidad !== 'all') filtered = filtered.filter(d => String(d['comunidad']) === valComunidad);

        // Guardar para gráficos globales
        currentData = filtered;

        // Actualizar contador superior
        document.getElementById('total-encuestas').innerText = `Total Encuestas: ${currentData.length}`;

        // Redibujar cuadros
        renderChart('chartPositivos', 'bar', 'Aspectos Positivos (%)', configAspectosPositivos);
        renderChart('chartNegativos', 'bar', 'Principales Problemas (%)', configAspectosNegativos);
        renderChart('chartExpectativas', 'bar', 'Expectativas Positivas (%)', configExpectativas);
        renderChart('chartMedios', 'line', 'Medios de Info. (%)', configMedios); // Line para variar
    }

    // FUNCIÓN PARA RENDERIZAR CUALQUIER GRAFICO DE BARRAS U OTROS
    function renderChart(canvasId, type, label, keysToCount) {
        const ctx = document.getElementById(canvasId).getContext('2d');

        // Destruir instancia previa si existe para evitar overlaying
        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }

        let labels = [];
        let dataPoints = [];
        const total = currentData.length;

        keysToCount.forEach(key => {
            // Contar cuantas encuestas tienen seleccionado 'key'
            // Ojo: en data.js, lo que marcaban aparecia como string del mismo nombre u otros valores.
            // Para ser robustos, si 'not null' y es string, lo contamos
            let count = currentData.filter(d => {
                let v = d[key];
                return v !== null && v !== "" && String(v).trim() !== "-";
            }).length;

            let pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;

            // Recortar label para que no quede inmenso
            let shortLabel = String(key).charAt(0).toUpperCase() + String(key).slice(1);
            if (shortLabel.length > 25) {
                shortLabel = shortLabel.substring(0, 25) + '...';
            }

            labels.push(shortLabel);
            dataPoints.push(pct);
        });

        // Colores combinados cyan-blue neon
        const clr1 = 'rgba(88, 166, 255, 0.7)';
        const clr2 = 'rgba(88, 166, 255, 1)';

        charts[canvasId] = new Chart(ctx, {
            type: type, // 'bar', 'line', 'pie', etc
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: dataPoints,
                    backgroundColor: type === 'line' ? 'rgba(88, 166, 255, 0.1)' : clr1,
                    borderColor: clr2,
                    borderWidth: 2,
                    fill: type === 'line',
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    datalabels: {
                        color: '#fff',
                        anchor: 'end',
                        align: type === 'line' ? 'top' : 'end',
                        formatter: function (value) {
                            return value > 0 ? value + '%' : '';
                        },
                        font: { weight: 'bold', size: 10 }
                    }
                },
                scales: type === 'bar' ? {
                    y: {
                        beginAtZero: true,
                        max: Math.min(100, Math.max(...dataPoints, 10) + 10), // Dar 10% de margen arriba
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                } : {}
            }
        });
    }

});
