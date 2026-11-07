const dashboardPeriodElement =
    document.getElementById(
        "voltify-dashboard-period"
    );

const validDashboardPeriods =
    new Set(
        [
            "day",
            "week",
            "month",
            "3months"
        ]
    );

let currentPeriod = "day";

if (dashboardPeriodElement) {
    try {
        const savedPeriod =
            JSON.parse(
                dashboardPeriodElement.textContent
            );

        if (
            validDashboardPeriods.has(
                savedPeriod
            )
        ) {
            currentPeriod =
                savedPeriod;
        }

    } catch (error) {
        console.error(
            "Voltify: no se pudo leer la preferencia del dashboard.",
            error
        );
    }
}

const voltifyCharts = {
    hourly: null,
    trend: null,
    comparison: null
};

let activeApplianceIndex = null;
let applianceResizeObserver = null;

const paletteSequence = [
    { main: "#7048ff", dark: "#0879e3" },
    { main: "#e42c39", dark: "#9E3137" },
    { main: "#49E5C2", dark: "#257765" },
    { main: "#F4B247", dark: "#9A6822" },
    { main: "#8B5CFF", dark: "#5230A6" },

    { main: "#FF8A5B", dark: "#944A31" },
    { main: "#A3E635", dark: "#5D7F20" },
    { main: "#C084FC", dark: "#6D3C9A" },
    { main: "#35D7FF", dark: "#1D7D93" },
    { main: "#F472B6", dark: "#8D3C69" },

    { main: "#FACC15", dark: "#8F7412" },
    { main: "#032ce3", dark: "#0817b7" },
    { main: "#60A5FA", dark: "#315B8E" },
    { main: "#FB7185", dark: "#963F4D" },
    { main: "#F97316", dark: "#91420E" },

    { main: "#A78BFA", dark: "#5E4F91" },
    { main: "#ee5522", dark: "#c74504" },
    { main: "#2DD4BF", dark: "#1D756B" },
    { main: "#E879F9", dark: "#82478B" },
    { main: "#94A3B8", dark: "#4B5567" },

    { main: "#FF4D4D", dark: "#922B2B" },
    { main: "#4ADE80", dark: "#267443" },
    { main: "#6366F1", dark: "#37398B" },
    { main: "#FFB703", dark: "#956A00" },
    { main: "#EC4899", dark: "#862956" },

    { main: "#0EA5E9", dark: "#075A80" },
    { main: "#FF6B35", dark: "#963B1D" },
    { main: "#10B981", dark: "#09684A" },
    { main: "#D946EF", dark: "#792887" },
    { main: "#EAB308", dark: "#826304" },

    { main: "#3B82F6", dark: "#214A8B" },
    { main: "#F43F5E", dark: "#8A2436" },
    { main: "#14B8A6", dark: "#0B675D" },
    { main: "#FB923C", dark: "#915323" },
    { main: "#7C3AED", dark: "#452087" },

    { main: "#84CC16", dark: "#4A720D" },
    { main: "#064a56", dark: "#076778" },
    { main: "#F052B5", dark: "#872E66" },
    { main: "#FFCC4D", dark: "#94772C" },
    { main: "#708DFF", dark: "#40518F" }
];

const applianceTypeRules = [
    {
        type: "ps5",
        keywords: [
            "playstation 5",
            "playstation5",
            "play 5",
            "play5",
            "ps5"
        ]
    },
    {
        type: "console",
        keywords: [
            "playstation",
            "ps4",
            "xbox",
            "nintendo",
            "switch",
            "consola",
            "gaming console"
        ]
    },
    {
        type: "tv",
        keywords: [
            "smart tv",
            "televisor",
            "television",
            "tv living",
            "tv dormitorio",
            "oled",
            "qled",
            "led tv"
        ]
    },
    {
        type: "monitor",
        keywords: [
            "monitor",
            "pantalla pc",
            "pantalla computador"
        ]
    },
    {
        type: "fridge",
        keywords: [
            "refrigerador",
            "refrigeradora",
            "frigorifico",
            "nevera",
            "refrigeracion"
        ]
    },
    {
        type: "freezer",
        keywords: [
            "freezer",
            "congelador",
            "congeladora"
        ]
    },
    {
        type: "computer",
        keywords: [
            "computador",
            "computadora",
            "pc gamer",
            "pc escritorio",
            "desktop",
            "torre pc",
            "all in one",
            "all-in-one"
        ]
    },
    {
        type: "laptop",
        keywords: [
            "notebook",
            "laptop",
            "macbook",
            "ultrabook"
        ]
    },
    {
        type: "phone",
        keywords: [
            "celular",
            "smartphone",
            "iphone",
            "telefono movil",
            "telefono celular",
            "movil"
        ]
    },
    {
        type: "tablet",
        keywords: [
            "tablet",
            "ipad"
        ]
    },
    {
        type: "charger",
        keywords: [
            "cargador",
            "carga rapida",
            "cargador usb",
            "usb-c",
            "usb c",
            "adaptador de corriente",
            "cargador inalambrico"
        ]
    },
    {
        type: "speaker",
        keywords: [
            "parlante",
            "parlantes",
            "speaker",
            "soundbar",
            "barra de sonido",
            "subwoofer",
            "equipo de musica",
            "amplificador",
            "minicomponente"
        ]
    },
    {
        type: "headphones",
        keywords: [
            "audifono",
            "audifonos",
            "auricular",
            "auriculares",
            "headset",
            "headphones"
        ]
    },
    {
        type: "router",
        keywords: [
            "router",
            "modem",
            "wifi",
            "wi-fi",
            "repetidor",
            "access point",
            "punto de acceso"
        ]
    },
    {
        type: "network",
        keywords: [
            "switch de red",
            "switch red",
            "network switch",
            "servidor",
            "server",
            "nas"
        ]
    },
    {
        type: "printer",
        keywords: [
            "impresora",
            "multifuncional",
            "scanner",
            "escaner"
        ]
    },
    {
        type: "projector",
        keywords: [
            "proyector",
            "data show",
            "datashow"
        ]
    },
    {
        type: "camera",
        keywords: [
            "camara",
            "cctv",
            "dvr",
            "nvr",
            "webcam"
        ]
    },
    {
        type: "washer",
        keywords: [
            "lavadora",
            "lavado de ropa"
        ]
    },
    {
        type: "dryer",
        keywords: [
            "secadora",
            "secado de ropa"
        ]
    },
    {
        type: "dishwasher",
        keywords: [
            "lavavajillas",
            "lavaplatos electrico",
            "lavaplatos"
        ]
    },
    {
        type: "iron",
        keywords: [
            "plancha de ropa",
            "plancha vapor",
            "plancha electrica",
            "plancha"
        ]
    },
    {
        type: "heater",
        keywords: [
            "calefactor",
            "estufa electrica",
            "estufa",
            "radiador",
            "termoventilador",
            "panel electrico",
            "calefaccion"
        ]
    },
    {
        type: "airconditioner",
        keywords: [
            "aire acondicionado",
            "climatizador",
            "climatizacion"
        ]
    },
    {
        type: "fan",
        keywords: [
            "ventilador",
            "abanico electrico",
            "ventilacion"
        ]
    },
    {
        type: "humidifier",
        keywords: [
            "humidificador",
            "deshumidificador",
            "purificador de aire",
            "purificador"
        ]
    },
    {
        type: "microwave",
        keywords: [
            "microondas",
            "micro onda"
        ]
    },
    {
        type: "oven",
        keywords: [
            "horno electrico",
            "horno"
        ]
    },
    {
        type: "airfryer",
        keywords: [
            "air fryer",
            "airfryer",
            "freidora de aire",
            "freidora"
        ]
    },
    {
        type: "kettle",
        keywords: [
            "hervidor",
            "tetera electrica",
            "kettle"
        ]
    },
    {
        type: "toaster",
        keywords: [
            "tostador",
            "tostadora",
            "sandwichera"
        ]
    },
    {
        type: "coffee",
        keywords: [
            "cafetera",
            "maquina de cafe",
            "espresso"
        ]
    },
    {
        type: "blender",
        keywords: [
            "licuadora",
            "juguera",
            "procesadora",
            "procesador de alimentos"
        ]
    },
    {
        type: "mixer",
        keywords: [
            "batidora",
            "amasadora"
        ]
    },
    {
        type: "ricecooker",
        keywords: [
            "arrocera",
            "olla electrica",
            "multicooker",
            "olla a presion electrica"
        ]
    },
    {
        type: "cooktop",
        keywords: [
            "encimera electrica",
            "cocina electrica",
            "placa electrica",
            "vitroceramica",
            "induccion"
        ]
    },
    {
        type: "extractor",
        keywords: [
            "campana",
            "extractor de aire",
            "extractor cocina"
        ]
    },
    {
        type: "vacuum",
        keywords: [
            "aspiradora",
            "robot aspirador",
            "roomba"
        ]
    },
    {
        type: "hairdryer",
        keywords: [
            "secador de pelo",
            "secador cabello",
            "alisador",
            "plancha de pelo"
        ]
    },
    {
        type: "waterheater",
        keywords: [
            "termo electrico",
            "calefon electrico",
            "calentador de agua",
            "boiler"
        ]
    },
    {
        type: "pump",
        keywords: [
            "bomba de agua",
            "bomba piscina",
            "bomba electrica"
        ]
    },
    {
        type: "light",
        keywords: [
            "ampolleta",
            "bombilla",
            "lampara",
            "foco led",
            "foco",
            "iluminacion",
            "luz led",
            "luminaria"
        ]
    },
    {
        type: "fluorescent",
        keywords: [
            "fluorescente",
            "tubo fluorescente",
            "tubo led"
        ]
    },
    {
        type: "ledstrip",
        keywords: [
            "tira led",
            "cinta led",
            "led strip"
        ]
    },
    {
        type: "other",
        keywords: []
    }
];


function normalizeText(value = "") {
    return String(value)
        .toLowerCase()
        .normalize("NFD")
        .replace(
            /[\u0300-\u036f]/g,
            ""
        )
        .trim();
}


function formatNumber(
    value,
    decimals = 2
) {
    return new Intl.NumberFormat(
        "es-CL",
        {
            minimumFractionDigits:
                decimals,

            maximumFractionDigits:
                decimals
        }
    ).format(
        Number(value) || 0
    );
}


function formatPercent(value) {
    const number =
        Number(value) || 0;

    const decimals =
        Math.abs(
            number
            -
            Math.round(number)
        )
        <
        0.05

            ? 0

            : 1;

    return formatNumber(
        number,
        decimals
    );
}


function removeSkeleton(element) {
    if (!element) {
        return;
    }

    element.classList.remove(
        "skeleton",
        "skeleton-card",
        "skeleton-chart"
    );
}


function countUp(
    element,
    finalValue,
    options = {}
) {
    if (!element) {
        return;
    }

    const duration =
        options.duration
        ||
        900;

    const decimals =
        options.decimals
        ||
        0;

    const prefix =
        options.prefix
        ||
        "";

    const suffix =
        options.suffix
        ||
        "";

    const startTime =
        performance.now();


    function update(currentTime) {
        const elapsed =
            currentTime
            -
            startTime;

        const progress =
            Math.min(
                elapsed
                /
                duration,

                1
            );

        const eased =
            1
            -
            Math.pow(
                1
                -
                progress,

                3
            );

        const value =
            (
                Number(finalValue)
                ||
                0
            )
            *
            eased;

        const formatted =
            decimals > 0

                ? formatNumber(
                    value,
                    decimals
                )

                : Math.round(
                    value
                ).toLocaleString(
                    "es-CL"
                );

        element.textContent =
            `${prefix}${formatted}${suffix}`;

        if (
            progress < 1
        ) {
            requestAnimationFrame(
                update
            );
        }
    }

    requestAnimationFrame(
        update
    );
}


function countUpCLP(
    element,
    finalValue
) {
    if (!element) {
        return;
    }

    const duration =
        900;

    const startTime =
        performance.now();


    function update(currentTime) {
        const elapsed =
            currentTime
            -
            startTime;

        const progress =
            Math.min(
                elapsed
                /
                duration,

                1
            );

        const eased =
            1
            -
            Math.pow(
                1
                -
                progress,

                3
            );

        const current =
            (
                Number(finalValue)
                ||
                0
            )
            *
            eased;

        element.textContent =
            "$"
            +
            Math.round(
                current
            ).toLocaleString(
                "es-CL"
            );

        if (
            progress < 1
        ) {
            requestAnimationFrame(
                update
            );
        }
    }

    requestAnimationFrame(
        update
    );
}


function updateDate() {
    const element =
        document.getElementById(
            "dashboardDate"
        );

    if (!element) {
        return;
    }

    const formatted =
        new Intl.DateTimeFormat(
            "es-CL",
            {
                day: "2-digit",
                month: "long",
                year: "numeric"
            }
        ).format(
            new Date()
        );

    element.textContent =
        formatted
            .charAt(0)
            .toUpperCase()
        +
        formatted.slice(1);
}


/* KPI */

function renderConsumptionKpi(data) {
    const card =
        document.getElementById(
            "kpiConsumption"
        );

    if (!card) {
        return;
    }

    removeSkeleton(card);

    const changeHtml =
        data.consumptionChange
        ===
        null

            ? `
                <span class="kpi-change">
                    Sin comparación
                </span>
            `

            : `
                <span
                    class="
                        kpi-change
                        ${
                            data.consumptionChange >= 0
                                ? "negative"
                                : "positive"
                        }
                    "
                >
                    ${
                        data.consumptionChange >= 0
                            ? "↑"
                            : "↓"
                    }

                    ${Math.abs(
                        data.consumptionChange
                    )}%
                </span>
            `;

    card.innerHTML = `
        <div class="kpi-content">

            <div class="kpi-icon">

                <svg
                    width="25"
                    height="25"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                >
                    <path
                        d="
                            M13 2
                            L5 14
                            H11
                            L10 22
                            L19 9
                            H13
                            Z
                        "
                    />
                </svg>

            </div>


            <div class="kpi-data">

                <span class="kpi-label">
                    Consumo total
                </span>


                <div class="kpi-value-row">

                    <span
                        class="kpi-value"
                        id="consumptionValue"
                    >
                        0
                    </span>

                    <span class="kpi-unit">
                        kWh
                    </span>

                    ${changeHtml}

                </div>


                <p class="kpi-note">
                    período seleccionado
                </p>

            </div>

        </div>
    `;

    countUp(
        document.getElementById(
            "consumptionValue"
        ),

        data.consumptionToday,

        {
            decimals: 2
        }
    );
}


function renderCostKpi(data) {
    const card =
        document.getElementById(
            "kpiCost"
        );

    if (!card) {
        return;
    }

    removeSkeleton(card);

    const includeFixedCharge =
        currentPeriod
        ===
        "month"
        ||
        currentPeriod
        ===
        "3months";

    const displayCost =
        includeFixedCharge

            ? data.estimatedBill

            : data.estimatedCost;

    const hasCost =
        displayCost
        !==
        null
        &&
        Number.isFinite(
            Number(
                displayCost
            )
        );

    let costNote =
        "tarifa aún no configurada";

    if (hasCost) {
        if (
            includeFixedCharge
            &&
            data.fixedChargeApplied
            !==
            null
        ) {
            const energyCost =
                Math.round(
                    Number(
                        data.energyCost
                    )
                    ||
                    0
                ).toLocaleString(
                    "es-CL"
                );

            const fixedCharge =
                Math.round(
                    Number(
                        data.fixedChargeApplied
                    )
                    ||
                    0
                ).toLocaleString(
                    "es-CL"
                );

            costNote =
                currentPeriod
                ===
                "month"

                    ? `energía $${energyCost} + cargo fijo $${fixedCharge}`

                    : `energía $${energyCost} + cargos fijos $${fixedCharge}`;

        } else {
            costNote =
                "costo energético estimado";
        }
    }

    card.innerHTML = `
        <div class="kpi-content">

            <div class="kpi-icon orange">

                <svg
                    width="25"
                    height="25"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                >
                    <ellipse
                        cx="12"
                        cy="6"
                        rx="7"
                        ry="3"
                    />

                    <path
                        d="
                            M5 6v5
                            c0 1.7 3.1 3 7 3
                            s7-1.3 7-3V6
                        "
                    />

                    <path
                        d="
                            M5 11v5
                            c0 1.7 3.1 3 7 3
                            s7-1.3 7-3v-5
                        "
                    />
                </svg>

            </div>


            <div class="kpi-data">

                <span class="kpi-label">
                    Costo estimado
                </span>


                <div class="kpi-value-row">

                    <span
                        class="kpi-value"
                        id="costValue"
                    >
                        ${
                            hasCost
                                ? "$0"
                                : "—"
                        }
                    </span>

                    ${
                        hasCost

                            ? `
                                <span class="kpi-unit">
                                    CLP
                                </span>
                            `

                            : ""
                    }

                </div>


                <p class="kpi-note">
                    ${costNote}
                </p>

            </div>

        </div>
    `;

    if (hasCost) {
        countUpCLP(
            document.getElementById(
                "costValue"
            ),

            displayCost
        );
    }
}


function renderDevicesKpi(data) {
    const card =
        document.getElementById(
            "kpiDevices"
        );

    if (!card) {
        return;
    }

    removeSkeleton(card);

    card.innerHTML = `
        <div class="kpi-content">

            <div class="kpi-icon">

                <svg
                    width="25"
                    height="25"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                >
                    <path d="M4 19V12"/>
                    <path d="M9 19V7"/>
                    <path d="M14 19V4"/>
                    <path d="M19 19V9"/>
                </svg>

            </div>


            <div class="kpi-data">

                <span class="kpi-label">
                    Artefactos activos
                </span>


                <div class="kpi-value-row">

                    <span class="kpi-value">

                        ${data.activeDevices}
                        /
                        ${data.totalDevices}

                    </span>

                </div>


                <p class="kpi-note">
                    dispositivos registrados
                </p>

            </div>

        </div>
    `;
}
function renderGoalKpi(data) {
    const card =
        document.getElementById(
            "kpiGoal"
        );

    if (!card) {
        return;
    }

    removeSkeleton(card);

    const goal =
        data.goal;

    if (!goal) {

        card.innerHTML = `
            <div class="kpi-content">

                <div class="kpi-icon target">

                    <svg
                        width="25"
                        height="25"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.8"
                    >
                        <circle
                            cx="12"
                            cy="12"
                            r="8"
                        />

                        <circle
                            cx="12"
                            cy="12"
                            r="4"
                        />

                        <path d="M12 2v4"/>
                        <path d="M22 12h-4"/>
                    </svg>

                </div>


                <div class="kpi-data">

                    <span class="kpi-label">
                        Progreso de meta
                    </span>


                    <div class="goal-value-row">

                        <span class="kpi-value">
                            Sin meta
                        </span>

                    </div>


                    <p class="kpi-note">
                        meta energética aún no configurada
                    </p>

                </div>

            </div>
        `;

        return;
    }


    const isCLP =
        goal.type
        ===
        "clp";


    const detail =
        isCLP

            ? `$${Math.round(
                goal.current
            ).toLocaleString(
                "es-CL"
            )}
            /
            $${Math.round(
                goal.target
            ).toLocaleString(
                "es-CL"
            )}`

            : `${formatNumber(
                goal.current,
                1
            )}
            /
            ${formatNumber(
                goal.target,
                0
            )}
            kWh`;


    card.innerHTML = `
        <div class="kpi-content">

            <div class="kpi-icon target">

                <svg
                    width="25"
                    height="25"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                >
                    <circle
                        cx="12"
                        cy="12"
                        r="8"
                    />

                    <circle
                        cx="12"
                        cy="12"
                        r="4"
                    />

                    <path d="M12 2v4"/>
                    <path d="M22 12h-4"/>
                </svg>

            </div>


            <div class="kpi-data">

                <span class="kpi-label">
                    Progreso de meta
                </span>


                <div class="goal-value-row">

                    <span
                        class="kpi-value"
                        id="goalValue"
                    >
                        0%
                    </span>

                    <span class="goal-detail">
                        ${detail}
                    </span>

                </div>


                <div class="goal-track">

                    <div
                        class="goal-progress"
                        id="goalProgress"
                    >
                    </div>

                </div>

            </div>

        </div>
    `;


    countUp(
        document.getElementById(
            "goalValue"
        ),

        goal.progress,

        {
            suffix: "%"
        }
    );


    requestAnimationFrame(
        () => {

            requestAnimationFrame(
                () => {

                    const progress =
                        document.getElementById(
                            "goalProgress"
                        );

                    if (progress) {

                        progress.style.width =
                            `${Math.min(
                                goal.progress,
                                100
                            )}%`;
                    }
                }
            );
        }
    );
}


function renderKpis(data) {
    renderConsumptionKpi(data);
    renderCostKpi(data);
    renderDevicesKpi(data);
    renderGoalKpi(data);
}


/* Gráficos */

function chartTextColor() {
    return "#7F8DA8";
}


function blueGradient() {
    return new echarts.graphic.LinearGradient(
        0,
        1,
        0,
        0,
        [
            {
                offset: 0,
                color: "#2457FF"
            },
            {
                offset: 0.55,
                color: "#438CFF"
            },
            {
                offset: 1,
                color: "#55B7FF"
            }
        ]
    );
}


function renderHourlyChart(data) {
    const element =
        document.getElementById(
            "hourlyChart"
        );

    if (!element) {
        return;
    }

    removeSkeleton(element);

    if (!voltifyCharts.hourly) {
        voltifyCharts.hourly =
            echarts.init(
                element
            );
    }


    const labels =
        data.hourlyConsumption.map(
            item =>
                item.hour
        );


    const values =
        data.hourlyConsumption.map(
            item =>
                item.value
        );


    voltifyCharts.hourly.setOption(
        {
            animation: true,

            animationDuration:
                950,

            animationDurationUpdate:
                500,

            animationEasing:
                "cubicOut",


            grid: {
                left: 46,
                right: 14,
                top: 24,
                bottom: 41
            },


            tooltip: {
                trigger:
                    "axis",

                backgroundColor:
                    "rgba(4,10,24,.96)",

                borderColor:
                    "rgba(75,140,255,.40)",

                textStyle: {
                    color:
                        "#F4F7FF"
                },


                formatter(params) {
                    const item =
                        params[0];

                    return `
                        <strong>
                            ${item.axisValue}
                        </strong>

                        <br>

                        Consumo:

                        <strong
                            style="
                                color:
                                #428CFF
                            "
                        >

                            ${formatNumber(
                                item.value,
                                2
                            )}

                            kWh

                        </strong>
                    `;
                }
            },


            xAxis: {
                type:
                    "category",

                data:
                    labels,


                axisTick: {
                    show:
                        false
                },


                axisLine: {
                    lineStyle: {
                        color:
                            "rgba(150,170,200,0.20)"
                    }
                },


                axisLabel: {
                    color:
                        chartTextColor(),

                    fontSize:
                        9,

                    interval:
                        currentPeriod
                        ===
                        "day"

                            ? 2

                            : 0
                }
            },


            yAxis: {
                type:
                    "value",

                name:
                    "kWh",


                nameTextStyle: {
                    color:
                        chartTextColor()
                },


                axisLabel: {
                    color:
                        chartTextColor(),

                    fontSize:
                        9
                },


                splitLine: {
                    lineStyle: {
                        color:
                            "rgba(80,120,180,0.08)"
                    }
                }
            },


            series: [
                {
                    type:
                        "bar",

                    data:
                        values,

                    barMaxWidth:
                        18,


                    itemStyle: {
                        color:
                            blueGradient(),

                        borderRadius:
                            [
                                5,
                                5,
                                1,
                                1
                            ],

                        shadowBlur:
                            7,

                        shadowColor:
                            "rgba(40,120,255,0.16)"
                    },


                    emphasis: {
                        itemStyle: {
                            color:
                                "#5AA2FF",

                            shadowBlur:
                                14,

                            shadowColor:
                                "rgba(66,140,255,0.38)"
                        }
                    },


                    animationDelay(index) {
                        return index * 22;
                    }
                }
            ]
        },

        true
    );
}


function renderTrendChart(data) {
    const element =
        document.getElementById(
            "trendChart"
        );

    if (!element) {
        return;
    }

    removeSkeleton(element);

    if (!voltifyCharts.trend) {
        voltifyCharts.trend =
            echarts.init(
                element
            );
    }


    const labels =
        data.trend.map(
            item =>
                item.day
        );


    const consumption =
        data.trend.map(
            item =>
                item.consumption
        );


    const useBillCost =
        currentPeriod
        ===
        "month"
        ||
        currentPeriod
        ===
        "3months";


    const costs =
        data.trend.map(
            item =>
                useBillCost

                    ? (
                        item.billCost
                        ??
                        item.cost
                    )

                    : item.cost
        );


    const hasCost =
        data.costAvailable
        ===
        true
        &&
        costs.some(
            value =>
                value
                !==
                null
                &&
                Number.isFinite(
                    Number(value)
                )
        );


    const yAxis = [
        {
            type:
                "value",

            name:
                "kWh",

            axisLabel: {
                color:
                    chartTextColor(),

                fontSize:
                    9
            },

            splitLine: {
                lineStyle: {
                    color:
                        "rgba(80,120,180,0.08)"
                }
            }
        }
    ];


    const series = [
        {
            name:
                "Consumo",

            type:
                "line",

            smooth:
                true,

            symbol:
                "circle",

            symbolSize:
                6,

            data:
                consumption,

            lineStyle: {
                width:
                    2.4,

                color:
                    "#3B82FF"
            },

            itemStyle: {
                color:
                    "#428CFF",

                borderColor:
                    "#AFCBFF",

                borderWidth:
                    1
            },

            areaStyle: {
                color:
                    new echarts.graphic.LinearGradient(
                        0,
                        0,
                        0,
                        1,
                        [
                            {
                                offset:
                                    0,

                                color:
                                    "rgba(59,130,255,0.18)"
                            },

                            {
                                offset:
                                    1,

                                color:
                                    "rgba(59,130,255,0.00)"
                            }
                        ]
                    )
            }
        }
    ];


    if (hasCost) {

        yAxis.push(
            {
                type:
                    "value",

                name:
                    "CLP",

                axisLabel: {
                    color:
                        chartTextColor(),

                    fontSize:
                        9
                },

                splitLine: {
                    show:
                        false
                }
            }
        );


        series.push(
            {
                name:
                    "Costo",

                type:
                    "line",

                yAxisIndex:
                    1,

                smooth:
                    true,

                symbol:
                    "circle",

                symbolSize:
                    5,

                data:
                    costs,

                lineStyle: {
                    width:
                        2,

                    type:
                        "dashed",

                    color:
                        "#8A5CFF"
                },

                itemStyle: {
                    color:
                        "#8A5CFF"
                }
            }
        );
    }


    voltifyCharts.trend.setOption(
        {
            animation:
                true,

            animationDuration:
                1000,

            animationDurationUpdate:
                500,

            animationEasing:
                "cubicOut",


            grid: {
                left:
                    43,

                right:
                    hasCost
                        ? 48
                        : 18,

                top:
                    42,

                bottom:
                    39
            },


            legend: {
                top:
                    0,

                textStyle: {
                    color:
                        "#9BA9C3"
                },

                data:
                    hasCost

                        ? [
                            "Consumo",
                            "Costo"
                        ]

                        : [
                            "Consumo"
                        ]
            },


            tooltip: {
                trigger:
                    "axis",

                backgroundColor:
                    "rgba(4,10,24,.96)",

                borderColor:
                    "rgba(75,140,255,.40)",

                textStyle: {
                    color:
                        "#F4F7FF"
                }
            },


            xAxis: {
                type:
                    "category",

                boundaryGap:
                    false,

                data:
                    labels,

                axisLine: {
                    lineStyle: {
                        color:
                            "rgba(150,170,200,0.20)"
                    }
                },

                axisLabel: {
                    color:
                        chartTextColor(),

                    fontSize:
                        9
                }
            },


            yAxis,

            series
        },

        true
    );
}


function renderComparisonChart(data) {
    const element =
        document.getElementById(
            "comparisonChart"
        );

    if (!element) {
        return;
    }

    removeSkeleton(element);

    if (!voltifyCharts.comparison) {
        voltifyCharts.comparison =
            echarts.init(
                element
            );
    }


    const labels =
        data.comparison.map(
            item =>
                item.hour
        );


    const current =
        data.comparison.map(
            item =>
                item.current
        );


    const previous =
        data.comparison.map(
            item =>
                item.previous
        );


    voltifyCharts.comparison.setOption(
        {
            animation:
                true,

            animationDuration:
                900,

            animationDurationUpdate:
                450,

            animationEasing:
                "cubicOut",


            grid: {
                left:
                    42,

                right:
                    14,

                top:
                    42,

                bottom:
                    39
            },


            legend: {
                top:
                    0,

                textStyle: {
                    color:
                        "#9BA9C3"
                },

                data: [
                    "Actual",
                    "Anterior"
                ]
            },


            tooltip: {
                trigger:
                    "axis",

                backgroundColor:
                    "rgba(4,10,24,.96)",

                borderColor:
                    "rgba(75,140,255,.40)",

                textStyle: {
                    color:
                        "#F4F7FF"
                }
            },


            xAxis: {
                type:
                    "category",

                data:
                    labels,


                axisTick: {
                    show:
                        false
                },


                axisLine: {
                    lineStyle: {
                        color:
                            "rgba(150,170,200,0.20)"
                    }
                },


                axisLabel: {
                    color:
                        chartTextColor(),

                    fontSize:
                        8
                }
            },


            yAxis: {
                type:
                    "value",

                name:
                    "kWh",


                axisLabel: {
                    color:
                        chartTextColor(),

                    fontSize:
                        8
                },


                splitLine: {
                    lineStyle: {
                        color:
                            "rgba(80,120,180,0.08)"
                    }
                }
            },


            series: [
                {
                    name:
                        "Actual",

                    type:
                        "bar",

                    data:
                        current,

                    barMaxWidth:
                        14,

                    itemStyle: {
                        color:
                            blueGradient(),

                        borderRadius:
                            [
                                4,
                                4,
                                0,
                                0
                            ]
                    }
                },

                {
                    name:
                        "Anterior",

                    type:
                        "bar",

                    data:
                        previous,

                    barMaxWidth:
                        14,

                    itemStyle: {
                        color:
                            new echarts.graphic.LinearGradient(
                                0,
                                1,
                                0,
                                0,
                                [
                                    {
                                        offset:
                                            0,

                                        color:
                                            "#453B78"
                                    },

                                    {
                                        offset:
                                            1,

                                        color:
                                            "#7857FF"
                                    }
                                ]
                            ),

                        opacity:
                            0.55,

                        borderRadius:
                            [
                                4,
                                4,
                                0,
                                0
                            ]
                    }
                }
            ]
        },

        true
    );
}


/* Detección de artefactos */

function detectApplianceType(item) {
    const name =
        normalizeText(
            item.name
            ||
            item.nombre
            ||
            item.artefacto
            ||
            ""
        );


    const category =
        normalizeText(
            item.category
            ||
            item.categoria
            ||
            item.cssClass
            ||
            ""
        );


    const brand =
        normalizeText(
            item.brand
            ||
            item.marca
            ||
            ""
        );


    const model =
        normalizeText(
            item.model
            ||
            item.modelo
            ||
            ""
        );


    const fullText =
        `${name} ${brand} ${model} ${category}`
            .trim();


    for (
        const rule
        of
        applianceTypeRules
    ) {

        if (
            rule.type
            ===
            "other"
        ) {
            continue;
        }


        if (
            rule.keywords.some(
                keyword =>
                    fullText.includes(
                        normalizeText(
                            keyword
                        )
                    )
            )
        ) {
            return rule.type;
        }
    }


    return "other";
}


function stablePaletteIndex(
    item,
    index
) {
    const raw =
        String(
            item.id
            ??
            item.artefacto_id
            ??
            item.name
            ??
            index
        );


    let hash =
        0;


    for (
        let i = 0;
        i < raw.length;
        i += 1
    ) {
        hash =
            (
                (
                    hash
                    <<
                    5
                )
                -
                hash
            )
            +
            raw.charCodeAt(
                i
            );

        hash |= 0;
    }


    return (
        Math.abs(
            hash
        )
        %
        paletteSequence.length
    );
}


function getPalette(
    item,
    index = 0
) {
    return paletteSequence[
        stablePaletteIndex(
            item,
            index
        )
    ];
}


function getArtifactMetadata(item) {
    if (
        typeof dashboardSource
        ===
        "undefined"
        ||
        !Array.isArray(
            dashboardSource.artefactos
        )
    ) {
        return {};
    }


    const id =
        Number(
            item.id
            ??
            item.artefacto_id
        );


    return (
        dashboardSource.artefactos.find(
            artefacto =>
                Number(
                    artefacto.id
                )
                ===
                id
        )
        ||
        {}
    );
}
/* Íconos */

function getApplianceIcon(
    type,
    size = 24,
    color = null
) {
    const stroke =
        color
        ||
        "#48A8FF";


    const base = `
        width="${size}"
        height="${size}"
        viewBox="0 0 24 24"
        fill="none"
        stroke="${stroke}"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        style="
            filter:
                drop-shadow(
                    0 0 4px
                    ${stroke}33
                );
        "
    `;


    switch (type) {

        case "tv":

            return `
                <svg ${base}>
                    <rect
                        x="3.5"
                        y="4.5"
                        width="17"
                        height="12"
                        rx="2"
                    />
                    <path d="M12 16.5V19"/>
                    <path d="M8.5 20h7"/>
                </svg>
            `;


        case "monitor":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="4"
                        width="18"
                        height="12"
                        rx="2"
                    />
                    <path d="M12 16v4"/>
                    <path d="M8 20h8"/>
                    <path d="M6 7h12"/>
                </svg>
            `;


        case "fridge":

            return `
                <svg ${base}>
                    <rect
                        x="6"
                        y="2.5"
                        width="12"
                        height="19"
                        rx="2"
                    />
                    <path d="M6 10h12"/>
                    <path d="M9 6v2"/>
                    <path d="M9 13v3"/>
                </svg>
            `;


        case "freezer":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="6"
                        width="16"
                        height="13"
                        rx="2"
                    />
                    <path d="M4 10h16"/>
                    <path d="M12 2.5v6"/>
                    <path d="M9.5 5.5 12 8l2.5-2.5"/>
                </svg>
            `;


        case "computer":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="4"
                        width="13"
                        height="10"
                        rx="1.5"
                    />
                    <path d="M9.5 14v3"/>
                    <path d="M6 18h7"/>
                    <rect
                        x="18"
                        y="5"
                        width="3"
                        height="12"
                        rx="1"
                    />
                    <circle
                        cx="19.5"
                        cy="14"
                        r=".5"
                    />
                </svg>
            `;


        case "laptop":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="4"
                        width="16"
                        height="11"
                        rx="1.5"
                    />
                    <path
                        d="
                            M2.8 18
                            h18.4
                            L19.8 20
                            H4.2
                            z
                        "
                    />
                    <path d="M9.5 18h5"/>
                </svg>
            `;


        case "ps5":

            return `
                <svg ${base}>
                    <path
                        d="
                            M9 3.5
                            c-1 2.5-1 14 0 17
                        "
                    />
                    <path
                        d="
                            M15 3.5
                            c1 2.5 1 14 0 17
                        "
                    />
                    <path d="M9 5.5h6"/>
                    <path d="M9 18.5h6"/>
                    <circle
                        cx="12"
                        cy="14.5"
                        r=".7"
                    />
                    <path d="M11 9.5h2"/>
                </svg>
            `;


        case "console":

            return `
                <svg ${base}>
                    <path
                        d="
                            M7 9h10
                            c2.5 0 4 2 4 4.6
                            0 2.4-1.4 4.4-3.2 4.4
                            -1.3 0-2.4-1-3.1-2
                            H9.3
                            c-.7 1-1.8 2-3.1 2
                            C4.4 18 3 16 3 13.6
                            3 11 4.5 9 7 9
                            z
                        "
                    />
                    <path d="M8 12v4"/>
                    <path d="M6 14h4"/>
                    <circle
                        cx="16.5"
                        cy="12.8"
                        r=".7"
                    />
                    <circle
                        cx="18.5"
                        cy="14.8"
                        r=".7"
                    />
                </svg>
            `;


        case "phone":

            return `
                <svg ${base}>
                    <rect
                        x="7"
                        y="2.5"
                        width="10"
                        height="19"
                        rx="2"
                    />
                    <path d="M11 18.5h2"/>
                </svg>
            `;


        case "tablet":

            return `
                <svg ${base}>
                    <rect
                        x="5"
                        y="2.5"
                        width="14"
                        height="19"
                        rx="2"
                    />
                    <circle
                        cx="12"
                        cy="18.5"
                        r=".7"
                    />
                </svg>
            `;


        case "charger":

            return `
                <svg ${base}>
                    <rect
                        x="7"
                        y="7"
                        width="7"
                        height="10"
                        rx="1"
                    />
                    <path d="M9 7V4"/>
                    <path d="M12 7V4"/>
                    <path
                        d="
                            M14 11h3
                            c2 0 3 1 3 3v2
                        "
                    />
                    <path d="M10 11l-1 2h2l-1 2"/>
                </svg>
            `;


        case "speaker":

            return `
                <svg ${base}>
                    <rect
                        x="6"
                        y="3"
                        width="12"
                        height="18"
                        rx="2"
                    />
                    <circle
                        cx="12"
                        cy="14"
                        r="4"
                    />
                    <circle
                        cx="12"
                        cy="7"
                        r="1.5"
                    />
                </svg>
            `;


        case "headphones":

            return `
                <svg ${base}>
                    <path
                        d="
                            M4 13v-2
                            a8 8 0 0 1 16 0v2
                        "
                    />
                    <rect
                        x="3"
                        y="12"
                        width="4"
                        height="7"
                        rx="2"
                    />
                    <rect
                        x="17"
                        y="12"
                        width="4"
                        height="7"
                        rx="2"
                    />
                </svg>
            `;


        case "router":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="14"
                        width="16"
                        height="5"
                        rx="1.5"
                    />
                    <path d="M8 14V9"/>
                    <path d="M16 14V9"/>
                    <path d="M6 7c1.2-1.2 2.4-1.8 4-2"/>
                    <path d="M18 7c-1.2-1.2-2.4-1.8-4-2"/>
                    <circle
                        cx="8"
                        cy="16.5"
                        r=".5"
                    />
                    <circle
                        cx="11"
                        cy="16.5"
                        r=".5"
                    />
                </svg>
            `;


        case "network":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="7"
                        width="18"
                        height="10"
                        rx="2"
                    />
                    <path d="M7 11h2"/>
                    <path d="M11 11h2"/>
                    <path d="M15 11h2"/>
                    <path d="M7 14h2"/>
                    <path d="M11 14h2"/>
                    <path d="M15 14h2"/>
                    <path d="M12 3v4"/>
                </svg>
            `;


        case "printer":

            return `
                <svg ${base}>
                    <path d="M6 8V3h12v5"/>
                    <rect
                        x="4"
                        y="8"
                        width="16"
                        height="9"
                        rx="2"
                    />
                    <path d="M7 14h10v7H7z"/>
                    <circle
                        cx="17"
                        cy="11"
                        r=".6"
                    />
                </svg>
            `;


        case "projector":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="7"
                        width="18"
                        height="10"
                        rx="2"
                    />
                    <circle
                        cx="15.5"
                        cy="12"
                        r="3"
                    />
                    <path d="M6 10h3"/>
                    <path d="M6 13h2"/>
                    <path d="M7 17v2"/>
                    <path d="M17 17v2"/>
                </svg>
            `;


        case "camera":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="7"
                        width="18"
                        height="12"
                        rx="2"
                    />
                    <circle
                        cx="12"
                        cy="13"
                        r="4"
                    />
                    <path d="M8 7l1.5-3h5L16 7"/>
                </svg>
            `;


        case "washer":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="3"
                        width="16"
                        height="18"
                        rx="2"
                    />
                    <circle
                        cx="12"
                        cy="13"
                        r="5"
                    />
                    <circle
                        cx="12"
                        cy="13"
                        r="2.2"
                    />
                    <path d="M7 6h2"/>
                    <circle
                        cx="17"
                        cy="6"
                        r=".8"
                    />
                </svg>
            `;


        case "dryer":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="3"
                        width="16"
                        height="18"
                        rx="2"
                    />
                    <circle
                        cx="12"
                        cy="13"
                        r="5"
                    />
                    <path
                        d="
                            M9.2 13
                            c1.1-2 4.5-2 5.6 0
                        "
                    />
                    <path d="M7 6h2"/>
                    <circle
                        cx="17"
                        cy="6"
                        r=".8"
                    />
                </svg>
            `;


        case "dishwasher":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="3"
                        width="16"
                        height="18"
                        rx="2"
                    />
                    <path d="M4 8h16"/>
                    <path d="M8 12h8"/>
                    <path d="M8 16h8"/>
                    <circle
                        cx="17"
                        cy="5.5"
                        r=".7"
                    />
                </svg>
            `;


        case "iron":

            return `
                <svg ${base}>
                    <path
                        d="
                            M4 17h16
                            l-3-8H8
                            z
                        "
                    />
                    <path d="M9 9c0-3 5-3 6 0"/>
                    <path d="M5 20h14"/>
                </svg>
            `;


        case "heater":

            return `
                <svg ${base}>
                    <path
                        d="
                            M13.4 2.5
                            C13.8 5.1 17.2 6.5 17.2 10.2
                            c0 2-.9 3.5-2.1 4.6
                            .4-2.4-.9-4-2.3-5.3
                            -.2 1.8-1.3 2.8-2.3 3.8
                            -1 1-1.7 2.1-1.7 3.5
                            0 2.4 1.4 4.2 3.4 4.2
                            3.5 0 6.5-2.7 6.5-6.7
                            0-4.9-3.2-7.5-5.3-11.8
                            z
                        "
                    />
                </svg>
            `;


        case "airconditioner":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="5"
                        width="18"
                        height="7"
                        rx="2"
                    />
                    <path d="M6 9h12"/>
                    <path d="M8 15c0 2-1.5 2-1.5 4"/>
                    <path d="M12 15c0 2-1.5 2-1.5 4"/>
                    <path d="M16 15c0 2-1.5 2-1.5 4"/>
                </svg>
            `;


        case "fan":

            return `
                <svg ${base}>
                    <circle
                        cx="12"
                        cy="11"
                        r="2"
                    />
                    <path d="M12 9c0-5 5-5 5-2 0 2-2 3-5 4"/>
                    <path d="M14 11c5 0 5 5 2 5-2 0-3-2-4-5"/>
                    <path d="M12 13c0 5-5 5-5 2 0-2 2-3 5-4"/>
                    <path d="M10 11c-5 0-5-5-2-5 2 0 3 2 4 5"/>
                    <path d="M12 13v7"/>
                    <path d="M8 20h8"/>
                </svg>
            `;


        case "humidifier":

            return `
                <svg ${base}>
                    <path
                        d="
                            M12 3
                            s5 5.4 5 9
                            a5 5 0 0 1-10 0
                            c0-3.6 5-9 5-9
                            z
                        "
                    />
                    <path d="M9 17c1.2 1.2 4.8 1.2 6 0"/>
                </svg>
            `;


        case "microwave":

            return `
                <svg ${base}>
                    <rect
                        x="2.5"
                        y="6"
                        width="19"
                        height="12"
                        rx="2"
                    />
                    <rect
                        x="5"
                        y="8.5"
                        width="9"
                        height="7"
                        rx="1"
                    />
                    <path d="M17 9h2"/>
                    <path d="M17 11h2"/>
                    <circle
                        cx="18"
                        cy="14"
                        r="1"
                    />
                    <path d="M6 18v1.5"/>
                    <path d="M18 18v1.5"/>
                </svg>
            `;


        case "oven":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="3"
                        width="16"
                        height="18"
                        rx="2"
                    />
                    <path d="M4 8h16"/>
                    <circle
                        cx="8"
                        cy="6"
                        r=".6"
                    />
                    <circle
                        cx="12"
                        cy="6"
                        r=".6"
                    />
                    <circle
                        cx="16"
                        cy="6"
                        r=".6"
                    />
                    <rect
                        x="7"
                        y="11"
                        width="10"
                        height="6"
                        rx="1"
                    />
                </svg>
            `;


        case "airfryer":

            return `
                <svg ${base}>
                    <path
                        d="
                            M7 4h10
                            l2 6-2 10H7
                            L5 10
                            z
                        "
                    />
                    <path d="M8 9h8"/>
                    <path d="M10 13h4"/>
                    <path d="M9 4V2h6v2"/>
                </svg>
            `;


        case "kettle":

            return `
                <svg ${base}>
                    <path d="M7 8h9l2 9H6z"/>
                    <path d="M9 8V5h5v3"/>
                    <path d="M16 10c3 0 4 1.4 4 3.2 0 1.7-1.1 2.8-3 3.1"/>
                    <path d="M8 20h8"/>
                </svg>
            `;


        case "toaster":

            return `
                <svg ${base}>
                    <rect
                        x="4"
                        y="8"
                        width="16"
                        height="10"
                        rx="3"
                    />
                    <path d="M8 8V5h8v3"/>
                    <path d="M7 18v2"/>
                    <path d="M17 18v2"/>
                    <path d="M8 12h8"/>
                </svg>
            `;


        case "coffee":

            return `
                <svg ${base}>
                    <path d="M6 7h10v11H6z"/>
                    <path d="M16 10h2a3 3 0 0 1 0 6h-2"/>
                    <path d="M8 4c0-1 1-1 1-2"/>
                    <path d="M12 4c0-1 1-1 1-2"/>
                </svg>
            `;


        case "blender":

            return `
                <svg ${base}>
                    <path d="M8 3h8l-1 9H9z"/>
                    <path d="M10 12h4l2 6H8z"/>
                    <path d="M8 21h8"/>
                    <path d="M12 12V7"/>
                </svg>
            `;


        case "mixer":

            return `
                <svg ${base}>
                    <path
                        d="
                            M6 5h9
                            a4 4 0 0 1 4 4v2
                            H8
                            a3 3 0 0 1-3-3V6
                            a1 1 0 0 1 1-1
                            z
                        "
                    />
                    <path d="M11 11v8"/>
                    <path d="M15 11v8"/>
                    <path d="M9 19h8"/>
                </svg>
            `;


        case "ricecooker":

            return `
                <svg ${base}>
                    <path d="M5 10h14l-1 9H6z"/>
                    <path d="M7 10V7h10v3"/>
                    <path d="M9 4c0-1 1-1 1-2"/>
                    <path d="M14 4c0-1 1-1 1-2"/>
                </svg>
            `;


        case "cooktop":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="5"
                        width="18"
                        height="14"
                        rx="2"
                    />
                    <circle
                        cx="8"
                        cy="10"
                        r="2.5"
                    />
                    <circle
                        cx="16"
                        cy="10"
                        r="2.5"
                    />
                    <circle
                        cx="8"
                        cy="16"
                        r="1.8"
                    />
                    <circle
                        cx="16"
                        cy="16"
                        r="1.8"
                    />
                </svg>
            `;


        case "extractor":

            return `
                <svg ${base}>
                    <path d="M7 4h10l3 8H4z"/>
                    <path d="M8 12v3h8v-3"/>
                    <path d="M10 18c0 1-1 1-1 2"/>
                    <path d="M14 18c0 1-1 1-1 2"/>
                </svg>
            `;


        case "vacuum":

            return `
                <svg ${base}>
                    <circle
                        cx="9"
                        cy="16"
                        r="5"
                    />
                    <path d="M14 16h3c2 0 3-1 3-3V5"/>
                    <path d="M18 5h4"/>
                    <path d="M7 16h4"/>
                </svg>
            `;


        case "hairdryer":

            return `
                <svg ${base}>
                    <path d="M4 8h11l4 3-4 3H4z"/>
                    <path d="M9 14l2 7h4l-2-7"/>
                    <path d="M19 8v6"/>
                </svg>
            `;


        case "waterheater":

            return `
                <svg ${base}>
                    <rect
                        x="6"
                        y="3"
                        width="12"
                        height="18"
                        rx="5"
                    />
                    <path
                        d="
                            M12 7
                            s3 3 3 5
                            a3 3 0 0 1-6 0
                            c0-2 3-5 3-5
                            z
                        "
                    />
                </svg>
            `;


        case "pump":

            return `
                <svg ${base}>
                    <circle
                        cx="10"
                        cy="12"
                        r="5"
                    />
                    <path d="M15 9h4v6h-4"/>
                    <path d="M5 12H2"/>
                    <path d="M19 12h3"/>
                    <path d="M10 7v10"/>
                </svg>
            `;


        case "light":

            return `
                <svg ${base}>
                    <path d="M9 18h6"/>
                    <path d="M10 21h4"/>
                    <path
                        d="
                            M8 13
                            c-1.1-1.2-2-2.6-2-4.5
                            a6 6 0 0 1 12 0
                            c0 1.9-.9 3.3-2 4.5
                            -.9 1-1.3 2-1.5 3
                            h-5
                            c-.2-1-.6-2-1.5-3
                            z
                        "
                    />
                </svg>
            `;


        case "fluorescent":

            return `
                <svg ${base}>
                    <rect
                        x="3"
                        y="9"
                        width="18"
                        height="6"
                        rx="3"
                    />
                    <path d="M6 9V6"/>
                    <path d="M18 9V6"/>
                    <path d="M6 15v3"/>
                    <path d="M18 15v3"/>
                </svg>
            `;


        case "ledstrip":

            return `
                <svg ${base}>
                    <path
                        d="
                            M3 8h14
                            a4 4 0 0 1 0 8H9
                        "
                    />
                    <circle cx="6" cy="8" r="1"/>
                    <circle cx="11" cy="8" r="1"/>
                    <circle cx="16" cy="8" r="1"/>
                    <circle cx="16" cy="16" r="1"/>
                    <circle cx="11" cy="16" r="1"/>
                </svg>
            `;


        default:

            return `
                <svg ${base}>
                    <rect
                        x="5"
                        y="5"
                        width="14"
                        height="14"
                        rx="3"
                    />
                    <path d="M9 3h6"/>
                    <path d="M9 21h6"/>
                    <circle
                        cx="12"
                        cy="12"
                        r="2"
                    />
                </svg>
            `;
    }
}
/* Normalización */

function normalizeAppliances(data) {
    const source =
        Array.isArray(
            data.appliances
        )

            ? data.appliances

            : [];


    const total =
        source.reduce(
            (
                sum,
                item
            ) => {

                const value =
                    Math.max(
                        0,

                        Number(
                            item.consumption
                            ??
                            item.consumptionKwh
                            ??
                            item.consumoKwh
                            ??
                            item.value
                            ??
                            0
                        )
                    );

                return sum + value;
            },

            0
        );


    return source.map(
        (
            item,
            index
        ) => {

            const metadata =
                getArtifactMetadata(
                    item
                );


            const merged = {
                ...item,

                brand:
                    item.brand
                    ??
                    item.marca
                    ??
                    metadata.marca
                    ??
                    "",

                model:
                    item.model
                    ??
                    item.modelo
                    ??
                    metadata.modelo
                    ??
                    "",

                power:
                    item.power
                    ??
                    item.potencia_nominal_w
                    ??
                    metadata.potencia_nominal_w
                    ??
                    null
            };


            const consumption =
                Math.max(
                    0,

                    Number(
                        item.consumption
                        ??
                        item.consumptionKwh
                        ??
                        item.consumoKwh
                        ??
                        item.value
                        ??
                        0
                    )
                );


            const type =
                detectApplianceType(
                    merged
                );


            const palette =
                getPalette(
                    merged,
                    index
                );


            return {
                ...merged,

                originalIndex:
                    index,

                id:
                    item.id
                    ??
                    `appliance-${index}`,

                name:
                    item.name
                    ??
                    item.nombre
                    ??
                    `Artefacto ${index + 1}`,

                consumption,

                percentage:
                    total > 0

                        ? (
                            consumption
                            /
                            total
                        )
                        *
                        100

                        : 0,

                type,

                color:
                    item.color
                    ??
                    palette.main,

                darkColor:
                    item.darkColor
                    ??
                    palette.dark
            };
        }
    );
}


function applianceSecondaryText(item) {
    const parts = [];

    if (item.brand) {
        parts.push(
            item.brand
        );
    }

    if (item.model) {
        parts.push(
            item.model
        );
    }

    return parts.join(
        " · "
    );
}


/* Ranking */

function renderRanking(data) {
    const element =
        document.getElementById(
            "topAppliances"
        );

    if (!element) {
        return;
    }

    removeSkeleton(element);


    const appliances =
        normalizeAppliances(
            data
        )
            .slice()
            .sort(
                (
                    a,
                    b
                ) =>
                    b.consumption
                    -
                    a.consumption
            )
            .slice(
                0,
                5
            );


    if (
        appliances.length
        ===
        0
    ) {

        element.innerHTML = `
            <div
                style="
                    min-height: 180px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    color: #7F8DA8;
                    padding: 20px;
                "
            >
                Aún no hay consumos registrados
                en este período.
            </div>
        `;

        return;
    }


    const maxConsumption =
        Math.max(
            ...appliances.map(
                item =>
                    item.consumption
            )
        );


    element.innerHTML = `
        <div class="top-list">

            ${
                appliances.map(
                    (
                        item,
                        index
                    ) => {

                        const width =
                            maxConsumption > 0

                                ? (
                                    item.consumption
                                    /
                                    maxConsumption
                                )
                                *
                                100

                                : 0;


                        const secondary =
                            applianceSecondaryText(
                                item
                            );


                        return `
                            <div class="top-row">

                                <span class="top-rank">
                                    ${index + 1}
                                </span>


                                <div class="top-device-icon">

                                    ${getApplianceIcon(
                                        item.type,
                                        25,
                                        item.color
                                    )}

                                </div>


                                <div class="top-device-info">

                                    <span class="top-device-name">
                                        ${item.name}
                                    </span>


                                    ${
                                        secondary

                                            ? `
                                                <span
                                                    style="
                                                        display: block;
                                                        font-size: 10px;
                                                        color: #71809c;
                                                        margin-top: 2px;
                                                        white-space: nowrap;
                                                        overflow: hidden;
                                                        text-overflow: ellipsis;
                                                    "
                                                >
                                                    ${secondary}
                                                </span>
                                            `

                                            : ""
                                    }


                                    <div class="top-bar-track">

                                        <div
                                            class="top-bar"
                                            data-width="${width}"
                                            style="
                                                background:
                                                    linear-gradient(
                                                        90deg,
                                                        ${item.darkColor},
                                                        ${item.color}
                                                    );
                                            "
                                        >
                                        </div>

                                    </div>

                                </div>


                                <span class="top-value">

                                    ${formatNumber(
                                        item.consumption,
                                        2
                                    )}

                                    kWh

                                </span>

                            </div>
                        `;
                    }
                ).join("")
            }

        </div>
    `;


    requestAnimationFrame(
        () => {

            requestAnimationFrame(
                () => {

                    element
                        .querySelectorAll(
                            ".top-bar"
                        )
                        .forEach(
                            bar => {

                                bar.style.width =
                                    `${bar.dataset.width}%`;
                            }
                        );
                }
            );
        }
    );
}


/* Donut */

function polarToCartesian(
    centerX,
    centerY,
    radius,
    angleDegrees
) {
    const angleRadians =
        (
            angleDegrees
            -
            90
        )
        *
        Math.PI
        /
        180;


    return {
        x:
            centerX
            +
            radius
            *
            Math.cos(
                angleRadians
            ),

        y:
            centerY
            +
            radius
            *
            Math.sin(
                angleRadians
            )
    };
}


function createDonutPath(
    cx,
    cy,
    outerRadius,
    innerRadius,
    startAngle,
    endAngle
) {
    const outerStart =
        polarToCartesian(
            cx,
            cy,
            outerRadius,
            endAngle
        );


    const outerEnd =
        polarToCartesian(
            cx,
            cy,
            outerRadius,
            startAngle
        );


    const innerStart =
        polarToCartesian(
            cx,
            cy,
            innerRadius,
            startAngle
        );


    const innerEnd =
        polarToCartesian(
            cx,
            cy,
            innerRadius,
            endAngle
        );


    const largeArcFlag =
        endAngle
        -
        startAngle
        <=
        180

            ? "0"

            : "1";


    return [
        "M",
        outerStart.x,
        outerStart.y,

        "A",
        outerRadius,
        outerRadius,
        0,
        largeArcFlag,
        0,
        outerEnd.x,
        outerEnd.y,

        "L",
        innerStart.x,
        innerStart.y,

        "A",
        innerRadius,
        innerRadius,
        0,
        largeArcFlag,
        1,
        innerEnd.x,
        innerEnd.y,

        "Z"
    ].join(
        " "
    );
}


/* Estilos dinámicos */

function ensureDynamicApplianceStyles() {
    if (
        document.getElementById(
            "voltify-dynamic-appliances-style"
        )
    ) {
        return;
    }


    const style =
        document.createElement(
            "style"
        );


    style.id =
        "voltify-dynamic-appliances-style";


    style.textContent = `

        #applianceChart {
            position: relative;
        }

        #applianceChart
        .appliance-callout::after {
            display: none !important;
        }

        #applianceChart
        .appliance-layout-shell {
            position: absolute;
            inset: 0;
            z-index: 4;
            pointer-events: none;
        }

        #applianceChart
        .appliance-column {
            position: absolute;
            top: 4px;
            bottom: 4px;
            width: 26%;
            display: flex;
            flex-direction: column;
            justify-content: space-evenly;
            gap: 9px;
            overflow-y: auto;
            overflow-x: hidden;
            scrollbar-width: thin;
            scrollbar-color:
                rgba(72,168,255,.28)
                transparent;
            pointer-events: auto;
            padding: 3px 5px;
        }

        #applianceChart
        .appliance-column::-webkit-scrollbar {
            width: 5px;
        }

        #applianceChart
        .appliance-column::-webkit-scrollbar-thumb {
            background:
                rgba(72,168,255,.24);
            border-radius: 20px;
        }

        #applianceChart
        .appliance-column.left {
            left: 0;
            align-items: flex-start;
        }

        #applianceChart
        .appliance-column.right {
            right: 0;
            align-items: flex-end;
        }

        #applianceChart
        .appliance-column.scroll-mode {
            justify-content: flex-start;
        }

        #applianceChart
        .appliance-callout {
            position: relative !important;
            left: auto !important;
            right: auto !important;
            top: auto !important;
            bottom: auto !important;
            min-width: 0;
            width: 100%;
            padding: 5px 4px;
            border-radius: 8px;
            cursor: pointer;
            outline: none;
            transition:
                opacity 180ms ease,
                transform 180ms ease,
                filter 180ms ease,
                background 180ms ease;
        }

        #applianceChart
        .appliance-column.right
        .appliance-callout {
            text-align: right;
        }

        #applianceChart
        .appliance-callout:focus-visible {
            background:
                rgba(66,140,255,.08);

            box-shadow:
                0 0 0 1px
                rgba(72,168,255,.20);
        }

        #applianceChart
        .appliance-callout-content {
            display: inline-flex;
            width: max-content;
            max-width: 100%;
            gap: 8px;
            align-items: flex-start;
        }

        #applianceChart
        .appliance-column.left
        .appliance-callout-content {
            margin-right: auto;
        }

        #applianceChart
        .appliance-column.right
        .appliance-callout-content {
            margin-left: auto;
            flex-direction: row-reverse;
        }

        #applianceChart
        .appliance-callout-icon {
            width: 23px;
            min-width: 23px;
            height: 23px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 2px;
        }

        #applianceChart
        .appliance-callout-text {
            min-width: 0;
        }

        #applianceChart
        .appliance-callout-meta {
            display: block;
            margin-top: 2px;
            font-size: 9px;
            color: #71809c;
            max-width: 130px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        #applianceChart
        .appliance-connectors-svg {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            z-index: 3;
            overflow: visible;
            pointer-events: none;
        }

        #applianceChart
        .appliance-connector-group {
            opacity: 0;
            transition:
                opacity 180ms ease,
                filter 180ms ease;
        }

        #applianceChart
        .appliance-connector-group.active {
            opacity: 1;
        }

        #applianceChart
        .appliance-connector-path {
            stroke-dasharray: 3 5;
            stroke-linecap: round;
            stroke-linejoin: round;
            stroke-dashoffset: 18;
        }

        #applianceChart
        .appliance-connector-group.active
        .appliance-connector-path {
            animation:
                voltifyConnectorDraw
                340ms
                ease-out
                forwards;
        }

        @keyframes voltifyConnectorDraw {

            from {
                stroke-dashoffset: 26;
                opacity: 0;
            }

            to {
                stroke-dashoffset: 0;
                opacity: .95;
            }
        }

        #applianceChart
        .appliance-donut-stage {
            z-index: 2;
        }

        @media (
            max-width: 650px
        ) {
            #applianceChart
            .appliance-column {
                width: 31%;
            }
        }
    `;


    document.head.appendChild(
        style
    );
}


/* Rotación */

function findBestDonutRotation(appliances) {
    if (
        appliances.length
        <=
        1
    ) {
        return 0;
    }


    const baseMiddleAngles =
        [];


    let startAngle =
        0;


    appliances.forEach(
        item => {

            const segmentAngle =
                item.percentage
                *
                3.6;


            baseMiddleAngles.push(
                startAngle
                +
                segmentAngle
                /
                2
            );


            startAngle +=
                segmentAngle;
        }
    );


    const idealDifference =
        appliances.length
        %
        2;


    let bestRotation =
        0;


    let bestScore =
        Infinity;


    for (
        let rotation = -180;
        rotation <= 180;
        rotation += 1
    ) {

        let left =
            0;

        let right =
            0;

        let axisPenalty =
            0;


        baseMiddleAngles.forEach(
            angle => {

                const point =
                    polarToCartesian(
                        0,
                        0,
                        1,
                        angle
                        +
                        rotation
                    );


                if (
                    point.x
                    <
                    0
                ) {
                    left += 1;

                } else {

                    right += 1;
                }


                const absoluteX =
                    Math.abs(
                        point.x
                    );


                if (
                    absoluteX
                    <
                    0.12
                ) {
                    axisPenalty +=
                        0.12
                        -
                        absoluteX;
                }
            }
        );


        const difference =
            Math.abs(
                left
                -
                right
            );


        const balancePenalty =
            Math.abs(
                difference
                -
                idealDifference
            );


        const score =
            balancePenalty
            *
            10000
            +
            axisPenalty
            *
            100
            +
            Math.abs(
                rotation
            )
            *
            0.05;


        if (
            score
            <
            bestScore
        ) {
            bestScore =
                score;

            bestRotation =
                rotation;
        }
    }


    return bestRotation;
}


/* Geometría */

function getSegmentGeometry(appliances) {
    const rotation =
        findBestDonutRotation(
            appliances
        );


    let startAngle =
        rotation;


    return appliances.map(
        (
            item,
            index
        ) => {

            const segmentAngle =
                item.percentage
                *
                3.6;


            const endAngle =
                startAngle
                +
                segmentAngle;


            const middleAngle =
                startAngle
                +
                segmentAngle
                /
                2;


            const outerPoint =
                polarToCartesian(
                    250,
                    175,
                    147,
                    middleAngle
                );


            const result = {
                index,

                item,

                startAngle,

                endAngle,

                middleAngle,

                normalizedX:
                    (
                        outerPoint.x
                        -
                        250
                    )
                    /
                    147,

                normalizedY:
                    (
                        outerPoint.y
                        -
                        175
                    )
                    /
                    147
            };


            startAngle =
                endAngle;


            return result;
        }
    );
}


function assignApplianceSides(geometry) {
    const left =
        [];

    const right =
        [];


    geometry.forEach(
        meta => {

            if (
                meta.normalizedX
                <
                0
            ) {
                left.push(
                    meta
                );

            } else {

                right.push(
                    meta
                );
            }
        }
    );


    left.sort(
        (
            a,
            b
        ) =>
            a.normalizedY
            -
            b.normalizedY
    );


    right.sort(
        (
            a,
            b
        ) =>
            a.normalizedY
            -
            b.normalizedY
    );


    return {
        left,
        right
    };
}


function getDonutTargetPoint(
    container,
    stage,
    meta
) {
    const svgPoint =
        polarToCartesian(
            250,
            175,
            147,
            meta.middleAngle
        );


    const transformedX =
        svgPoint.x;


    const transformedY =
        28
        +
        svgPoint.y
        *
        0.69;


    const containerRect =
        container
            .getBoundingClientRect();


    const stageRect =
        stage
            .getBoundingClientRect();


    return {
        x:
            stageRect.left
            -
            containerRect.left
            +
            (
                transformedX
                /
                500
            )
            *
            stageRect.width,

        y:
            stageRect.top
            -
            containerRect.top
            +
            (
                transformedY
                /
                350
            )
            *
            stageRect.height
    };
}


function getLabelAnchorPoint(
    callout,
    containerRect,
    side
) {
    const content =
        callout.querySelector(
            ".appliance-callout-content"
        );


    const rect =
        (
            content
            ||
            callout
        ).getBoundingClientRect();


    const visualMargin =
        12;


    return {
        x:
            side
            ===
            "left"

                ? rect.right
                    -
                    containerRect.left
                    +
                    visualMargin

                : rect.left
                    -
                    containerRect.left
                    -
                    visualMargin,

        y:
            rect.top
            -
            containerRect.top
            +
            rect.height
            /
            2
    };
}


function createDynamicConnectorPath(
    source,
    target,
    side
) {
    const horizontalDistance =
        Math.abs(
            target.x
            -
            source.x
        );


    const firstHorizontalRun =
        horizontalDistance
        *
        0.58;


    const finalHorizontalRun =
        horizontalDistance
        *
        0.16;


    const direction =
        side
        ===
        "left"

            ? 1

            : -1;


    const c1 = {
        x:
            source.x
            +
            direction
            *
            firstHorizontalRun,

        y:
            source.y
    };


    const c2 = {
        x:
            target.x
            -
            direction
            *
            finalHorizontalRun,

        y:
            target.y
    };


    return `
        M
        ${target.x}
        ${target.y}

        C
        ${c2.x}
        ${c2.y},

        ${c1.x}
        ${c1.y},

        ${source.x}
        ${source.y}
    `;
}
/* Columnas */

function buildApplianceColumns(
    container,
    appliances,
    assignment
) {
    const shell =
        container.querySelector(
            ".appliance-layout-shell"
        );


    if (!shell) {
        return;
    }


    const leftIndexes =
        new Set(
            assignment.left.map(
                meta =>
                    meta.index
            )
        );


    function makeCallout(meta) {
        const item =
            appliances[
                meta.index
            ];


        const side =
            leftIndexes.has(
                meta.index
            )

                ? "left"

                : "right";


        const secondary =
            applianceSecondaryText(
                item
            );


        return `
            <div
                class="appliance-callout"
                data-index="${meta.index}"
                data-side="${side}"
                tabindex="0"
                role="button"

                aria-label="
                    ${item.name},
                    ${formatPercent(
                        item.percentage
                    )}
                    por ciento,
                    ${formatNumber(
                        item.consumption,
                        2
                    )}
                    kilowatt-hora
                "

                style="
                    color:
                    ${item.color};
                "
            >

                <div class="appliance-callout-content">

                    <div class="appliance-callout-icon">

                        ${getApplianceIcon(
                            item.type,
                            20,
                            item.color
                        )}

                    </div>


                    <div class="appliance-callout-text">

                        <span class="appliance-callout-name">
                            ${item.name}
                        </span>


                        ${
                            secondary

                                ? `
                                    <span class="appliance-callout-meta">
                                        ${secondary}
                                    </span>
                                `

                                : ""
                        }


                        <span class="appliance-callout-percent">

                            ${formatPercent(
                                item.percentage
                            )}%

                        </span>


                        <span class="appliance-callout-kwh">

                            ${formatNumber(
                                item.consumption,
                                2
                            )}

                            kWh

                        </span>

                    </div>

                </div>

            </div>
        `;
    }


    shell.innerHTML = `

        <div
            class="
                appliance-column
                left
                ${
                    assignment.left.length > 6
                        ? "scroll-mode"
                        : ""
                }
            "
            data-side="left"
        >

            ${
                assignment.left
                    .map(
                        makeCallout
                    )
                    .join("")
            }

        </div>


        <div
            class="
                appliance-column
                right
                ${
                    assignment.right.length > 6
                        ? "scroll-mode"
                        : ""
                }
            "
            data-side="right"
        >

            ${
                assignment.right
                    .map(
                        makeCallout
                    )
                    .join("")
            }

        </div>
    `;
}


/* Conectores */

function rebuildApplianceConnectors(
    container,
    appliances,
    geometry,
    assignment
) {
    const stage =
        container.querySelector(
            ".appliance-donut-stage"
        );


    const svg =
        container.querySelector(
            ".appliance-connectors-svg"
        );


    if (
        !stage
        ||
        !svg
    ) {
        return;
    }


    const containerRect =
        container
            .getBoundingClientRect();


    const assignmentMap =
        new Map();


    assignment.left.forEach(
        meta =>
            assignmentMap.set(
                meta.index,
                "left"
            )
    );


    assignment.right.forEach(
        meta =>
            assignmentMap.set(
                meta.index,
                "right"
            )
    );


    svg.innerHTML =
        geometry
            .map(
                meta => {

                    const side =
                        assignmentMap.get(
                            meta.index
                        );


                    const callout =
                        container.querySelector(
                            `.appliance-callout[data-index="${meta.index}"]`
                        );


                    if (
                        !callout
                        ||
                        !side
                    ) {
                        return "";
                    }


                    const target =
                        getDonutTargetPoint(
                            container,
                            stage,
                            meta
                        );


                    const source =
                        getLabelAnchorPoint(
                            callout,
                            containerRect,
                            side
                        );


                    const item =
                        appliances[
                            meta.index
                        ];


                    const path =
                        createDynamicConnectorPath(
                            source,
                            target,
                            side
                        );


                    return `
                        <g
                            class="
                                appliance-connector-group
                            "
                            data-index="${meta.index}"
                        >

                            <path
                                class="
                                    appliance-connector-path
                                "
                                d="${path}"
                                fill="none"
                                stroke="${item.color}"
                                stroke-width="1.5"
                                opacity="0.95"

                                style="
                                    filter:
                                        drop-shadow(
                                            0 0 2px
                                            ${item.color}55
                                        );
                                "
                            />


                            <circle
                                cx="${target.x}"
                                cy="${target.y}"
                                r="4"
                                fill="${item.color}"
                                opacity="0.12"
                            />


                            <circle
                                cx="${target.x}"
                                cy="${target.y}"
                                r="2.1"
                                fill="${item.color}"
                                opacity="1"
                            />

                        </g>
                    `;
                }
            )
            .join("");
}


/* Interacción */

function setActiveAppliance(
    container,
    index,
    showTooltip = false,
    event = null
) {
    activeApplianceIndex =
        index;


    container
        .querySelectorAll(
            ".donut-segment-group"
        )
        .forEach(
            segment => {

                const current =
                    Number(
                        segment.dataset.index
                    );


                if (
                    current
                    ===
                    index
                ) {
                    segment.style.opacity =
                        "1";

                    segment.style.transform =
                        "translateY(-7px) scale(1.025)";

                    segment.style.filter =
                        "brightness(1.15) saturate(1.08)";

                } else {

                    segment.style.opacity =
                        "0.62";

                    segment.style.transform =
                        "";

                    segment.style.filter =
                        "";
                }
            }
        );


    container
        .querySelectorAll(
            ".appliance-callout"
        )
        .forEach(
            label => {

                const current =
                    Number(
                        label.dataset.index
                    );


                if (
                    current
                    ===
                    index
                ) {
                    label.style.opacity =
                        "1";

                    label.style.filter =
                        "brightness(1.18)";

                    label.style.transform =
                        "scale(1.025)";

                } else {

                    label.style.opacity =
                        "0.60";

                    label.style.filter =
                        "";

                    label.style.transform =
                        "";
                }
            }
        );


    container
        .querySelectorAll(
            ".appliance-connector-group"
        )
        .forEach(
            connector => {

                connector.classList.toggle(
                    "active",

                    Number(
                        connector.dataset.index
                    )
                    ===
                    index
                );
            }
        );


    if (
        showTooltip
        &&
        event
    ) {

        const data =
            dashboardData[
                currentPeriod
            ];


        const appliances =
            normalizeAppliances(
                data
            );


        const item =
            appliances[
                index
            ];


        if (item) {

            const tooltip =
                getDashboardTooltip();


            const estimatedCost =
                data.estimatedCost
                ===
                null

                    ? null

                    : data.estimatedCost
                        *
                        (
                            item.percentage
                            /
                            100
                        );


            const secondary =
                applianceSecondaryText(
                    item
                );


            const powerText =
                item.power
                !==
                null
                &&
                item.power
                !==
                undefined

                    ? `${formatNumber(
                        item.power,
                        2
                    )} W`

                    : "";


            tooltip.innerHTML = `

                <strong>
                    ${item.name}
                </strong>


                ${
                    secondary

                        ? `
                            <br>

                            <span
                                style="
                                    color:
                                    #8fa0bd;
                                "
                            >
                                ${secondary}
                            </span>
                        `

                        : ""
                }


                ${
                    powerText

                        ? `
                            <br>

                            <span
                                style="
                                    color:
                                    #8fa0bd;
                                "
                            >
                                Potencia nominal:
                                ${powerText}
                            </span>
                        `

                        : ""
                }


                <br><br>


                Consumo:

                <span
                    style="
                        color:
                        ${item.color};
                    "
                >

                    ${formatNumber(
                        item.consumption,
                        2
                    )}

                    kWh

                </span>


                <br>


                Participación:

                ${formatPercent(
                    item.percentage
                )}%


                <br>


                ${
                    estimatedCost
                    ===
                    null

                        ? "Costo estimado: No disponible"

                        : `
                            Costo estimado:
                            $${Math.round(
                                estimatedCost
                            ).toLocaleString(
                                "es-CL"
                            )}
                            CLP
                        `
                }
            `;


            tooltip.classList.add(
                "visible"
            );


            moveTooltip(
                event,
                tooltip
            );
        }
    }
}


function clearActiveAppliance(container) {
    activeApplianceIndex =
        null;


    container
        .querySelectorAll(
            ".donut-segment-group"
        )
        .forEach(
            segment => {

                segment.style.opacity =
                    "1";

                segment.style.transform =
                    "";

                segment.style.filter =
                    "";
            }
        );


    container
        .querySelectorAll(
            ".appliance-callout"
        )
        .forEach(
            label => {

                label.style.opacity =
                    "1";

                label.style.transform =
                    "";

                label.style.filter =
                    "";
            }
        );


    container
        .querySelectorAll(
            ".appliance-connector-group"
        )
        .forEach(
            connector => {

                connector.classList.remove(
                    "active"
                );
            }
        );


    const tooltip =
        document.querySelector(
            ".dashboard-tooltip"
        );


    if (tooltip) {

        tooltip.classList.remove(
            "visible"
        );
    }
}


function bindApplianceInteractions(container) {
    const segments =
        container.querySelectorAll(
            ".donut-segment-group"
        );


    const labels =
        container.querySelectorAll(
            ".appliance-callout"
        );


    function bindTarget(
        target,
        index
    ) {

        target.addEventListener(
            "mouseenter",

            event =>
                setActiveAppliance(
                    container,
                    index,
                    true,
                    event
                )
        );


        target.addEventListener(
            "mousemove",

            event => {

                const tooltip =
                    document.querySelector(
                        ".dashboard-tooltip.visible"
                    );


                if (tooltip) {

                    moveTooltip(
                        event,
                        tooltip
                    );
                }
            }
        );


        target.addEventListener(
            "mouseleave",

            () =>
                clearActiveAppliance(
                    container
                )
        );


        target.addEventListener(
            "click",

            event => {

                event.stopPropagation();


                if (
                    activeApplianceIndex
                    ===
                    index
                ) {
                    clearActiveAppliance(
                        container
                    );

                } else {

                    setActiveAppliance(
                        container,
                        index,
                        false
                    );
                }
            }
        );


        target.addEventListener(
            "focus",

            () =>
                setActiveAppliance(
                    container,
                    index,
                    false
                )
        );


        target.addEventListener(
            "blur",

            () =>
                clearActiveAppliance(
                    container
                )
        );


        target.addEventListener(
            "keydown",

            event => {

                if (
                    event.key
                    ===
                    "Enter"
                    ||
                    event.key
                    ===
                    " "
                ) {

                    event.preventDefault();


                    if (
                        activeApplianceIndex
                        ===
                        index
                    ) {
                        clearActiveAppliance(
                            container
                        );

                    } else {

                        setActiveAppliance(
                            container,
                            index,
                            false
                        );
                    }
                }


                if (
                    event.key
                    ===
                    "Escape"
                ) {

                    clearActiveAppliance(
                        container
                    );


                    target.blur();
                }
            }
        );
    }


    segments.forEach(
        segment =>
            bindTarget(
                segment,

                Number(
                    segment.dataset.index
                )
            )
    );


    labels.forEach(
        label =>
            bindTarget(
                label,

                Number(
                    label.dataset.index
                )
            )
    );


    container
        .querySelectorAll(
            ".appliance-column"
        )
        .forEach(
            column => {

                column.addEventListener(
                    "scroll",

                    () =>
                        scheduleApplianceLayout(
                            container,

                            dashboardData[
                                currentPeriod
                            ]
                        ),

                    {
                        passive:
                            true
                    }
                );
            }
        );
}


function scheduleApplianceLayout(
    container,
    data
) {
    requestAnimationFrame(
        () => {

            const appliances =
                normalizeAppliances(
                    data
                );


            if (
                !appliances.length
            ) {
                return;
            }


            const geometry =
                getSegmentGeometry(
                    appliances
                );


            const assignment =
                assignApplianceSides(
                    geometry
                );


            rebuildApplianceConnectors(
                container,
                appliances,
                geometry,
                assignment
            );
        }
    );
}
/* Donut 3D */

function renderApplianceChart(data) {
    const container =
        document.getElementById(
            "applianceChart"
        );


    if (!container) {
        return;
    }


    ensureDynamicApplianceStyles();


    removeSkeleton(
        container
    );


    const appliances =
        normalizeAppliances(
            data
        );


    if (
        appliances.length
        ===
        0
    ) {

        container.innerHTML = `
            <div
                style="
                    min-height: 320px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    color: #7F8DA8;
                    padding: 24px;
                "
            >
                Aún no hay consumos registrados
                en este período.
            </div>
        `;


        if (
            applianceResizeObserver
        ) {
            applianceResizeObserver
                .disconnect();
        }


        return;
    }


    const total =
        appliances.reduce(
            (
                sum,
                item
            ) =>
                sum
                +
                item.consumption,

            0
        );


    const geometry =
        getSegmentGeometry(
            appliances
        );


    const assignment =
        assignApplianceSides(
            geometry
        );


    let svgSegments =
        "";


    geometry
        .slice()
        .sort(
            (
                a,
                b
            ) =>
                a.normalizedY
                -
                b.normalizedY
        )
        .forEach(
            meta => {

                const item =
                    appliances[
                        meta.index
                    ];


                const segmentAngle =
                    meta.endAngle
                    -
                    meta.startAngle;


                const gap =
                    Math.min(
                        3.0,

                        Math.max(
                            0.45,

                            segmentAngle
                            *
                            0.11
                        )
                    );


                const start =
                    meta.startAngle
                    +
                    gap
                    /
                    2;


                const end =
                    meta.endAngle
                    -
                    gap
                    /
                    2;


                const path =
                    createDonutPath(
                        250,
                        175,
                        146,
                        82,
                        start,
                        end
                    );


                let depthLayers =
                    "";


                for (
                    let depth = 52;
                    depth >= 2;
                    depth -= 2
                ) {

                    const depthProgress =
                        depth
                        /
                        52;


                    const sideBrightness =
                        0.72
                        +
                        (
                            1
                            -
                            depthProgress
                        )
                        *
                        0.28;


                    depthLayers += `
                        <path
                            d="${path}"
                            fill="${item.darkColor}"

                            transform="
                                translate(
                                    0
                                    ${depth}
                                )
                            "

                            opacity="1"

                            style="
                                filter:
                                    brightness(
                                        ${sideBrightness}
                                    )
                                    saturate(
                                        1.05
                                    );
                            "
                        />
                    `;
                }


                svgSegments += `

                    <g
                        class="
                            donut-segment-group
                        "

                        data-index="${meta.index}"

                        tabindex="0"

                        role="button"

                        aria-label="
                            ${item.name},
                            ${formatPercent(
                                item.percentage
                            )}
                            por ciento,
                            ${formatNumber(
                                item.consumption,
                                2
                            )}
                            kilowatt-hora
                        "

                        style="
                            transform-box:
                                fill-box;

                            transform-origin:
                                center;

                            transition:
                                transform 220ms ease,
                                filter 220ms ease,
                                opacity 220ms ease;

                            cursor:
                                pointer;

                            outline:
                                none;
                        "
                    >

                        ${depthLayers}


                        <defs>

                            <linearGradient
                                id="
                                    topHighlight-${meta.index}
                                "

                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                            >

                                <stop
                                    offset="0%"
                                    stop-color="#ffffff"
                                    stop-opacity="0.32"
                                />

                                <stop
                                    offset="45%"
                                    stop-color="#ffffff"
                                    stop-opacity="0.10"
                                />

                                <stop
                                    offset="100%"
                                    stop-color="#ffffff"
                                    stop-opacity="0"
                                />

                            </linearGradient>

                        </defs>


                        <path
                            d="${path}"

                            fill="${item.color}"

                            stroke="
                                rgba(
                                    225,
                                    238,
                                    255,
                                    .58
                                )
                            "

                            stroke-width="1.4"

                            style="
                                filter:
                                    drop-shadow(
                                        0
                                        2px
                                        5px
                                        rgba(
                                            0,
                                            0,
                                            0,
                                            .30
                                        )
                                    )

                                    drop-shadow(
                                        0
                                        0
                                        9px
                                        ${item.color}66
                                    );
                            "
                        />


                        <path
                            d="${path}"

                            fill="
                                url(
                                    #topHighlight-${meta.index}
                                )
                            "

                            pointer-events="none"
                        />

                    </g>
                `;
            }
        );


    container.innerHTML = `

        <svg
            class="
                appliance-connectors-svg
            "

            xmlns="
                http://www.w3.org/2000/svg
            "

            aria-hidden="true"
        >
        </svg>


        <div
            class="
                appliance-donut-stage
            "
        >

            <svg
                class="
                    appliance-donut-svg
                "

                viewBox="
                    0 0 500 350
                "

                xmlns="
                    http://www.w3.org/2000/svg
                "
            >

                <ellipse
                    cx="250"
                    cy="263"
                    rx="165"
                    ry="34"

                    fill="
                        rgba(
                            0,
                            0,
                            0,
                            .38
                        )
                    "
                />


                <g
                    transform="
                        translate(
                            0
                            28
                        )

                        scale(
                            1
                            .69
                        )
                    "
                >

                    ${svgSegments}

                </g>

            </svg>


            <div class="donut-center">

                <span
                    class="
                        donut-center-label
                    "
                >
                    Total
                </span>


                <span
                    class="
                        donut-center-value
                    "
                >
                    ${formatNumber(
                        total,
                        2
                    )}
                </span>


                <span
                    class="
                        donut-center-unit
                    "
                >
                    kWh
                </span>

            </div>

        </div>


        <div
            class="
                appliance-layout-shell
            "
        >
        </div>
    `;


    buildApplianceColumns(
        container,
        appliances,
        assignment
    );


    requestAnimationFrame(
        () => {

            rebuildApplianceConnectors(
                container,
                appliances,
                geometry,
                assignment
            );


            bindApplianceInteractions(
                container
            );
        }
    );


    if (
        applianceResizeObserver
    ) {
        applianceResizeObserver
            .disconnect();
    }


    if (
        "ResizeObserver"
        in
        window
    ) {

        applianceResizeObserver =
            new ResizeObserver(
                () =>
                    scheduleApplianceLayout(
                        container,
                        data
                    )
            );


        applianceResizeObserver
            .observe(
                container
            );
    }
}


/* Tooltip */

function getDashboardTooltip() {
    let tooltip =
        document.querySelector(
            ".dashboard-tooltip"
        );


    if (!tooltip) {

        tooltip =
            document.createElement(
                "div"
            );


        tooltip.className =
            "dashboard-tooltip";


        document.body.appendChild(
            tooltip
        );
    }


    return tooltip;
}


function moveTooltip(
    event,
    tooltip
) {
    tooltip.style.left =
        `${event.clientX + 16}px`;


    tooltip.style.top =
        `${event.clientY + 16}px`;
}


/* Dashboard */

function updateMainChartTitle() {
    const title =
        document.querySelector(
            ".dashboard-main-grid .dashboard-card:first-child .dashboard-card-title"
        );


    if (!title) {
        return;
    }


    const titles = {
        day:
            "Consumo por hora",

        week:
            "Consumo por día",

        month:
            "Consumo por semana",

        "3months":
            "Consumo por mes"
    };


    title.textContent =
        titles[
            currentPeriod
        ];
}


function updateDashboardPeriodLabels() {
    const mainChart =
        document.getElementById(
            "hourlyChart"
        );

    const trendChart =
        document.getElementById(
            "trendChart"
        );


    const mainSelect =
        mainChart
            ?.closest(
                ".dashboard-card"
            )
            ?.querySelector(
                ".card-select"
            );


    const trendSelect =
        trendChart
            ?.closest(
                ".dashboard-card"
            )
            ?.querySelector(
                ".card-select"
            );


    const mainLabels = {
        day:
            "Hoy",

        week:
            "Últimos 7 días",

        month:
            "Mes actual",

        "3months":
            "Últimos 3 meses"
    };


    const trendLabels = {
        day:
            "Últimos 7 días",

        week:
            "Últimas 4 semanas",

        month:
            "Últimos 4 meses",

        "3months":
            "Últimos 6 meses"
    };


    if (
        mainSelect
        &&
        mainSelect.options.length
        >
        0
    ) {
        mainSelect.options[0].textContent =
            mainLabels[
                currentPeriod
            ];
    }


    if (
        trendSelect
        &&
        trendSelect.options.length
        >
        0
    ) {
        trendSelect.options[0].textContent =
            trendLabels[
                currentPeriod
            ];
    }
}


function renderDashboard(period) {
    const data =
        dashboardData[
            period
        ];


    if (!data) {
        return;
    }


    currentPeriod =
        period;


    activeApplianceIndex =
        null;


    updateMainChartTitle();


    updateDashboardPeriodLabels();


    renderKpis(
        data
    );


    renderHourlyChart(
        data
    );


    renderApplianceChart(
        data
    );


    renderTrendChart(
        data
    );


    renderRanking(
        data
    );


    renderComparisonChart(
        data
    );
}


/* Controles */

async function saveDashboardPeriodPreference(
    period
) {
    const form =
        document.getElementById(
            "dashboardPreferenceForm"
        );

    if (
        !form
        ||
        !validDashboardPeriods.has(
            period
        )
    ) {
        return;
    }

    const formData =
        new FormData(
            form
        );

    formData.set(
        "periodo",
        period
    );

    try {
        const response =
            await fetch(
                form.action,
                {
                    method: "POST",
                    body: formData,
                    credentials: "same-origin",
                    headers: {
                        "X-Requested-With":
                            "XMLHttpRequest"
                    }
                }
            );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

    } catch (error) {
        console.error(
            "Voltify: no se pudo guardar la preferencia del dashboard.",
            error
        );
    }
}


function configurePeriodButtons() {
    const buttons =
        document.querySelectorAll(
            ".period-button"
        );


    buttons.forEach(
        button => {

            button.classList.toggle(
                "active",
                button.dataset.period
                    ===
                    currentPeriod
            );


            button.addEventListener(
                "click",

                () => {

                    const period =
                        button.dataset.period;


                    if (
                        !validDashboardPeriods.has(
                            period
                        )
                    ) {
                        return;
                    }


                    buttons.forEach(
                        item =>
                            item.classList.remove(
                                "active"
                            )
                    );


                    button.classList.add(
                        "active"
                    );


                    renderDashboard(
                        period
                    );


                    saveDashboardPeriodPreference(
                        period
                    );
                }
            );
        }
    );
}


function configureMobileMenu() {
    const button =
        document.getElementById(
            "dashboardMobileMenu"
        );


    const sidebar =
        document.getElementById(
            "dashboardSidebar"
        );


    if (
        !button
        ||
        !sidebar
    ) {
        return;
    }


    button.addEventListener(
        "click",

        () =>
            sidebar.classList.toggle(
                "open"
            )
    );
}


function resizeCharts() {
    Object.values(
        voltifyCharts
    ).forEach(
        chart => {

            if (chart) {
                chart.resize();
            }
        }
    );


    const container =
        document.getElementById(
            "applianceChart"
        );


    const data =
        dashboardData[
            currentPeriod
        ];


    if (
        container
        &&
        data
    ) {
        scheduleApplianceLayout(
            container,
            data
        );
    }
}


/* Inicio */

function initializeDashboard() {
    updateDate();


    configurePeriodButtons();


    configureMobileMenu();


    renderDashboard(
        currentPeriod
    );


    window.addEventListener(
        "resize",
        resizeCharts
    );


    document.addEventListener(
        "click",

        event => {

            const container =
                document.getElementById(
                    "applianceChart"
                );


            if (
                !container
                ||
                container.contains(
                    event.target
                )
            ) {
                return;
            }


            clearActiveAppliance(
                container
            );
        }
    );
}


/* ECharts */

function loadECharts() {
    return new Promise(
        (
            resolve,
            reject
        ) => {

            if (
                typeof echarts
                !==
                "undefined"
            ) {

                resolve();

                return;
            }


            const script =
                document.createElement(
                    "script"
                );


            script.src =
                "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js";


            script.onload =
                resolve;


            script.onerror =
                () => {

                    reject(
                        new Error(
                            "No se pudo cargar ECharts."
                        )
                    );
                };


            document.head.appendChild(
                script
            );
        }
    );
}


document.addEventListener(
    "DOMContentLoaded",

    async () => {

        if (
            typeof dashboardData
            ===
            "undefined"
        ) {

            console.error(
                "Voltify: dashboard-data.js no fue cargado."
            );


            return;
        }


        try {

            await loadECharts();


            setTimeout(
                () => {

                    initializeDashboard();

                },

                260
            );


        } catch (error) {

            console.error(
                "Voltify:",
                error
            );
        }
    }
);