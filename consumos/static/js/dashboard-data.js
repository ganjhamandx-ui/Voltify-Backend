const dashboardSourceElement = document.getElementById(
    "voltify-dashboard-source"
);

const dashboardSource = dashboardSourceElement
    ? JSON.parse(dashboardSourceElement.textContent)
    : {
        artefactos: [],
        consumos: [],
        tarifa: {
            disponible: false,
            fuente: "sin_configurar",
            valor_kwh: null,
            cargo_fijo_mensual: null,
            empresa: "",
            comuna: ""
        },
        meta: {
            disponible: false,
            meta_consumo_kwh: null,
            meta_costo_clp: null,
            mes: null,
            anio: null
        }
    };

const sourceArtifacts = Array.isArray(
    dashboardSource.artefactos
)
    ? dashboardSource.artefactos
    : [];

const sourceConsumptions = Array.isArray(
    dashboardSource.consumos
)
    ? dashboardSource.consumos
        .map(item => ({
            ...item,
            consumo_kwh:
                Number(
                    item.consumo_kwh
                )
                ||
                0,
            parsedDate:
                new Date(
                    item.fecha
                )
        }))
        .filter(
            item =>
                !Number.isNaN(
                    item.parsedDate.getTime()
                )
        )
    : [];

const sourceTariff = (
    dashboardSource.tarifa
    &&
    typeof dashboardSource.tarifa
    ===
    "object"
)
    ? dashboardSource.tarifa
    : {};

const sourceMeta = (
    dashboardSource.meta
    &&
    typeof dashboardSource.meta
    ===
    "object"
)
    ? dashboardSource.meta
    : {};

const tariffRate =
    Number(
        sourceTariff.valor_kwh
    );

const monthlyFixedCharge =
    Number(
        sourceTariff.cargo_fijo_mensual
    );

const tariffAvailable = (
    sourceTariff.disponible
    ===
    true
    &&
    Number.isFinite(
        tariffRate
    )
    &&
    tariffRate > 0
    &&
    Number.isFinite(
        monthlyFixedCharge
    )
    &&
    monthlyFixedCharge >= 0
);


function startOfDay(date) {
    const result =
        new Date(
            date
        );

    result.setHours(
        0,
        0,
        0,
        0
    );

    return result;
}


function addDays(
    date,
    amount
) {
    const result =
        new Date(
            date
        );

    result.setDate(
        result.getDate()
        +
        amount
    );

    return result;
}


function startOfMonth(date) {
    return new Date(
        date.getFullYear(),
        date.getMonth(),
        1
    );
}


function addMonths(
    date,
    amount
) {
    return new Date(
        date.getFullYear(),
        date.getMonth()
        +
        amount,
        1
    );
}


function filterConsumptions(
    start,
    end
) {
    return sourceConsumptions.filter(
        item => (
            item.parsedDate
            >=
            start
            &&
            item.parsedDate
            <
            end
        )
    );
}


function sumConsumptions(items) {
    return items.reduce(
        (
            total,
            item
        ) =>
            total
            +
            item.consumo_kwh,
        0
    );
}


function calculateChange(
    current,
    previous
) {
    if (
        previous <= 0
    ) {
        return null;
    }

    return Number(
        (
            (
                (
                    current
                    -
                    previous
                )
                /
                previous
            )
            *
            100
        ).toFixed(1)
    );
}


function calculateEnergyCost(
    consumption
) {
    if (
        !tariffAvailable
    ) {
        return null;
    }

    return Number(
        (
            consumption
            *
            tariffRate
        ).toFixed(2)
    );
}


function calculateBillTotal(
    consumption,
    fixedChargeMonths
) {
    if (
        !tariffAvailable
    ) {
        return null;
    }

    const energyCost =
        consumption
        *
        tariffRate;

    const fixedCost =
        monthlyFixedCharge
        *
        fixedChargeMonths;

    return Number(
        (
            energyCost
            +
            fixedCost
        ).toFixed(2)
    );
}


function buildMonthlyGoal() {
    if (
        sourceMeta.disponible
        !==
        true
    ) {
        return null;
    }

    const currentDate =
        new Date();

    const metaMonth =
        Number(
            sourceMeta.mes
        );

    const metaYear =
        Number(
            sourceMeta.anio
        );

    if (
        Number.isFinite(
            metaMonth
        )
        &&
        Number.isFinite(
            metaYear
        )
        &&
        (
            metaMonth
            !==
            currentDate.getMonth() + 1
            ||
            metaYear
            !==
            currentDate.getFullYear()
        )
    ) {
        return null;
    }

    const currentMonthStart =
        startOfMonth(
            currentDate
        );

    const currentMonthEnd =
        addMonths(
            currentMonthStart,
            1
        );

    const monthlyConsumption =
        Number(
            sumConsumptions(
                filterConsumptions(
                    currentMonthStart,
                    currentMonthEnd
                )
            ).toFixed(2)
        );

    const consumptionTarget =
        Number(
            sourceMeta.meta_consumo_kwh
        );

    if (
        Number.isFinite(
            consumptionTarget
        )
        &&
        consumptionTarget > 0
    ) {
        return {
            type:
                "kwh",

            current:
                monthlyConsumption,

            target:
                consumptionTarget,

            progress:
                Number(
                    (
                        monthlyConsumption
                        /
                        consumptionTarget
                        *
                        100
                    ).toFixed(1)
                )
        };
    }

    const costTarget =
        Number(
            sourceMeta.meta_costo_clp
        );

    if (
        Number.isFinite(
            costTarget
        )
        &&
        costTarget > 0
        &&
        tariffAvailable
    ) {
        const monthlyBill =
            calculateBillTotal(
                monthlyConsumption,
                1
            );

        if (
            monthlyBill
            ===
            null
        ) {
            return null;
        }

        return {
            type:
                "clp",

            current:
                monthlyBill,

            target:
                costTarget,

            progress:
                Number(
                    (
                        monthlyBill
                        /
                        costTarget
                        *
                        100
                    ).toFixed(1)
                )
        };
    }

    return null;
}


function shortDayLabel(date) {
    return new Intl.DateTimeFormat(
        "es-CL",
        {
            weekday:
                "short"
        }
    )
        .format(
            date
        )
        .replace(
            ".",
            ""
        )
        .replace(
            /^./,
            value =>
                value.toUpperCase()
        );
}


function shortDateLabel(date) {
    return new Intl.DateTimeFormat(
        "es-CL",
        {
            day:
                "2-digit",

            month:
                "2-digit"
        }
    ).format(
        date
    );
}


function shortMonthLabel(date) {
    return new Intl.DateTimeFormat(
        "es-CL",
        {
            month:
                "short"
        }
    )
        .format(
            date
        )
        .replace(
            ".",
            ""
        )
        .replace(
            /^./,
            value =>
                value.toUpperCase()
        );
}


function buildAppliances(items) {
    const totals =
        new Map();

    items.forEach(
        item => {
            const key =
                String(
                    item.artefacto_id
                );

            const current =
                totals.get(
                    key
                )
                ||
                {
                    id:
                        item.artefacto_id,

                    name:
                        item.artefacto,

                    category:
                        item.categoria
                        ||
                        "Otros",

                    consumption:
                        0
                };

            current.consumption +=
                item.consumo_kwh;

            totals.set(
                key,
                current
            );
        }
    );

    return Array.from(
        totals.values()
    )
        .filter(
            item =>
                item.consumption
                >
                0
        )
        .sort(
            (
                a,
                b
            ) =>
                b.consumption
                -
                a.consumption
        )
        .map(
            item => ({
                ...item,

                consumption:
                    Number(
                        item.consumption
                            .toFixed(2)
                    ),

                estimatedCost:
                    calculateEnergyCost(
                        item.consumption
                    )
            })
        );
}


function isMonitoring(value) {
    return (
        value === true
        ||
        value === 1
        ||
        value === "1"
        ||
        value === "true"
    );
}


function activeDevices() {
    return sourceArtifacts.filter(
        artefacto =>
            isMonitoring(
                artefacto.monitoreando
            )
    ).length;
}


function buildHourlySeries(items) {
    const values =
        Array.from(
            {
                length:
                    24
            },

            () =>
                0
        );

    items.forEach(
        item => {
            values[
                item.parsedDate
                    .getHours()
            ] +=
                item.consumo_kwh;
        }
    );

    return values.map(
        (
            value,
            hour
        ) => ({
            hour:
                `${
                    String(
                        hour
                    ).padStart(
                        2,
                        "0"
                    )
                }:00`,

            value:
                Number(
                    value.toFixed(2)
                )
        })
    );
}


function buildDailySeries(
    start,
    days
) {
    return Array.from(
        {
            length:
                days
        },

        (
            _,
            index
        ) => {
            const dayStart =
                addDays(
                    start,
                    index
                );

            const dayEnd =
                addDays(
                    dayStart,
                    1
                );

            return {
                hour:
                    shortDayLabel(
                        dayStart
                    ),

                value:
                    Number(
                        sumConsumptions(
                            filterConsumptions(
                                dayStart,
                                dayEnd
                            )
                        ).toFixed(2)
                    )
            };
        }
    );
}


function buildWeeklySeries(
    monthStart,
    monthEnd
) {
    const weeks = [];

    let cursor =
        new Date(
            monthStart
        );

    let week = 1;

    while (
        cursor
        <
        monthEnd
    ) {
        const next =
            new Date(
                Math.min(
                    addDays(
                        cursor,
                        7
                    ).getTime(),

                    monthEnd.getTime()
                )
            );

        weeks.push(
            {
                hour:
                    `Semana ${week}`,

                value:
                    Number(
                        sumConsumptions(
                            filterConsumptions(
                                cursor,
                                next
                            )
                        ).toFixed(2)
                    )
            }
        );

        cursor = next;

        week += 1;
    }

    return weeks;
}


function buildMonthlySeries(
    start,
    months
) {
    return Array.from(
        {
            length:
                months
        },

        (
            _,
            index
        ) => {
            const monthStart =
                addMonths(
                    start,
                    index
                );

            const monthEnd =
                addMonths(
                    monthStart,
                    1
                );

            return {
                hour:
                    shortMonthLabel(
                        monthStart
                    ),

                value:
                    Number(
                        sumConsumptions(
                            filterConsumptions(
                                monthStart,
                                monthEnd
                            )
                        ).toFixed(2)
                    )
            };
        }
    );
}


function buildDayComparison(
    todayStart
) {
    const current =
        buildHourlySeries(
            filterConsumptions(
                todayStart,

                addDays(
                    todayStart,
                    1
                )
            )
        );

    const previousStart =
        addDays(
            todayStart,
            -1
        );

    const previous =
        buildHourlySeries(
            filterConsumptions(
                previousStart,
                todayStart
            )
        );

    return current
        .filter(
            (
                _,
                index
            ) =>
                index
                %
                2
                ===
                0
        )
        .map(
            (
                item,
                index
            ) => {
                const sourceIndex =
                    index
                    *
                    2;

                return {
                    hour:
                        item.hour,

                    current:
                        Number(
                            (
                                current[
                                    sourceIndex
                                ].value
                                +
                                (
                                    current[
                                        sourceIndex
                                        +
                                        1
                                    ]?.value
                                    ||
                                    0
                                )
                            ).toFixed(2)
                        ),

                    previous:
                        Number(
                            (
                                previous[
                                    sourceIndex
                                ].value
                                +
                                (
                                    previous[
                                        sourceIndex
                                        +
                                        1
                                    ]?.value
                                    ||
                                    0
                                )
                            ).toFixed(2)
                        )
                };
            }
        );
}


function buildWeekComparison(
    weekStart
) {
    const previousWeekStart =
        addDays(
            weekStart,
            -7
        );

    return Array.from(
        {
            length:
                7
        },

        (
            _,
            index
        ) => {
            const currentStart =
                addDays(
                    weekStart,
                    index
                );

            const currentEnd =
                addDays(
                    currentStart,
                    1
                );

            const previousStart =
                addDays(
                    previousWeekStart,
                    index
                );

            const previousEnd =
                addDays(
                    previousStart,
                    1
                );

            return {
                hour:
                    shortDayLabel(
                        currentStart
                    ),

                current:
                    Number(
                        sumConsumptions(
                            filterConsumptions(
                                currentStart,
                                currentEnd
                            )
                        ).toFixed(2)
                    ),

                previous:
                    Number(
                        sumConsumptions(
                            filterConsumptions(
                                previousStart,
                                previousEnd
                            )
                        ).toFixed(2)
                    )
            };
        }
    );
}


function buildMonthComparison(
    currentStart,
    currentEnd
) {
    const previousStart =
        addMonths(
            currentStart,
            -1
        );

    const previousEnd =
        currentStart;

    const currentWeeks =
        buildWeeklySeries(
            currentStart,
            currentEnd
        );

    const previousWeeks =
        buildWeeklySeries(
            previousStart,
            previousEnd
        );

    const length =
        Math.max(
            currentWeeks.length,
            previousWeeks.length
        );

    return Array.from(
        {
            length
        },

        (
            _,
            index
        ) => ({
            hour:
                `Semana ${index + 1}`,

            current:
                currentWeeks[
                    index
                ]?.value
                ||
                0,

            previous:
                previousWeeks[
                    index
                ]?.value
                ||
                0
        })
    );
}


function buildThreeMonthComparison(
    currentStart
) {
    const previousStart =
        addMonths(
            currentStart,
            -3
        );

    return Array.from(
        {
            length:
                3
        },

        (
            _,
            index
        ) => {
            const currentMonth =
                addMonths(
                    currentStart,
                    index
                );

            const currentEnd =
                addMonths(
                    currentMonth,
                    1
                );

            const previousMonth =
                addMonths(
                    previousStart,
                    index
                );

            const previousEnd =
                addMonths(
                    previousMonth,
                    1
                );

            return {
                hour:
                    shortMonthLabel(
                        currentMonth
                    ),

                current:
                    Number(
                        sumConsumptions(
                            filterConsumptions(
                                currentMonth,
                                currentEnd
                            )
                        ).toFixed(2)
                    ),

                previous:
                    Number(
                        sumConsumptions(
                            filterConsumptions(
                                previousMonth,
                                previousEnd
                            )
                        ).toFixed(2)
                    )
            };
        }
    );
}


function buildTrend(
    start,
    units,
    unitType
) {
    return Array.from(
        {
            length:
                units
        },

        (
            _,
            index
        ) => {
            let itemStart;
            let itemEnd;
            let label;

            let fixedChargeMonths =
                0;

            if (
                unitType
                ===
                "day"
            ) {
                itemStart =
                    addDays(
                        start,
                        index
                    );

                itemEnd =
                    addDays(
                        itemStart,
                        1
                    );

                label =
                    shortDateLabel(
                        itemStart
                    );

            } else if (
                unitType
                ===
                "week"
            ) {
                itemStart =
                    addDays(
                        start,
                        index
                        *
                        7
                    );

                itemEnd =
                    addDays(
                        itemStart,
                        7
                    );

                label =
                    `Sem ${index + 1}`;

            } else {
                itemStart =
                    addMonths(
                        start,
                        index
                    );

                itemEnd =
                    addMonths(
                        itemStart,
                        1
                    );

                label =
                    shortMonthLabel(
                        itemStart
                    );

                fixedChargeMonths =
                    1;
            }

            const consumption =
                Number(
                    sumConsumptions(
                        filterConsumptions(
                            itemStart,
                            itemEnd
                        )
                    ).toFixed(2)
                );

            return {
                day:
                    label,

                consumption,

                cost:
                    calculateEnergyCost(
                        consumption
                    ),

                billCost:
                    calculateBillTotal(
                        consumption,
                        fixedChargeMonths
                    )
            };
        }
    );
}


function makePeriodData({
    start,
    end,
    previousStart,
    previousEnd,
    mainSeries,
    trend,
    comparison,
    fixedChargeMonths
}) {
    const currentItems =
        filterConsumptions(
            start,
            end
        );

    const previousItems =
        filterConsumptions(
            previousStart,
            previousEnd
        );

    const currentTotal =
        sumConsumptions(
            currentItems
        );

    const previousTotal =
        sumConsumptions(
            previousItems
        );

    const currentEnergyCost =
        calculateEnergyCost(
            currentTotal
        );

    const previousEnergyCost =
        calculateEnergyCost(
            previousTotal
        );

    const currentBillTotal =
        calculateBillTotal(
            currentTotal,
            fixedChargeMonths
        );

    const previousBillTotal =
        calculateBillTotal(
            previousTotal,
            fixedChargeMonths
        );

    const fixedChargeApplied =
        tariffAvailable

            ? Number(
                (
                    monthlyFixedCharge
                    *
                    fixedChargeMonths
                ).toFixed(2)
            )

            : null;

    return {
        consumptionToday:
            Number(
                currentTotal
                    .toFixed(2)
            ),

        consumptionChange:
            calculateChange(
                currentTotal,
                previousTotal
            ),

        estimatedCost:
            currentEnergyCost,

        costChange:
            (
                currentEnergyCost
                !==
                null
                &&
                previousEnergyCost
                !==
                null
            )

                ? calculateChange(
                    currentEnergyCost,
                    previousEnergyCost
                )

                : null,

        costAvailable:
            tariffAvailable,

        energyCost:
            currentEnergyCost,

        estimatedBill:
            currentBillTotal,

        previousEstimatedBill:
            previousBillTotal,

        fixedChargeApplied,

        fixedChargeMonths,

        tariff: {
            available:
                tariffAvailable,

            source:
                sourceTariff.fuente
                ||
                "sin_configurar",

            rate:
                tariffAvailable
                    ? tariffRate
                    : null,

            monthlyFixedCharge:
                tariffAvailable
                    ? monthlyFixedCharge
                    : null,

            company:
                sourceTariff.empresa
                ||
                "",

            commune:
                sourceTariff.comuna
                ||
                ""
        },

        activeDevices:
            activeDevices(),

        totalDevices:
            sourceArtifacts.length,

        goal:
            buildMonthlyGoal(),

        hourlyConsumption:
            mainSeries,

        appliances:
            buildAppliances(
                currentItems
            ),

        trend,

        comparison
    };
}


const now =
    new Date();

const todayStart =
    startOfDay(
        now
    );

const tomorrowStart =
    addDays(
        todayStart,
        1
    );

const weekStart =
    addDays(
        todayStart,
        -6
    );

const weekEnd =
    tomorrowStart;

const previousWeekStart =
    addDays(
        weekStart,
        -7
    );

const previousWeekEnd =
    weekStart;

const monthStart =
    startOfMonth(
        now
    );

const monthEnd =
    addMonths(
        monthStart,
        1
    );

const previousMonthStart =
    addMonths(
        monthStart,
        -1
    );

const previousMonthEnd =
    monthStart;

const threeMonthStart =
    addMonths(
        monthStart,
        -2
    );

const threeMonthEnd =
    monthEnd;

const previousThreeMonthStart =
    addMonths(
        threeMonthStart,
        -3
    );

const previousThreeMonthEnd =
    threeMonthStart;


const dashboardData = {

    day:
        makePeriodData({

            start:
                todayStart,

            end:
                tomorrowStart,

            previousStart:
                addDays(
                    todayStart,
                    -1
                ),

            previousEnd:
                todayStart,

            mainSeries:
                buildHourlySeries(
                    filterConsumptions(
                        todayStart,
                        tomorrowStart
                    )
                ),

            trend:
                buildTrend(
                    addDays(
                        todayStart,
                        -6
                    ),
                    7,
                    "day"
                ),

            comparison:
                buildDayComparison(
                    todayStart
                ),

            fixedChargeMonths:
                0
        }),


    week:
        makePeriodData({

            start:
                weekStart,

            end:
                weekEnd,

            previousStart:
                previousWeekStart,

            previousEnd:
                previousWeekEnd,

            mainSeries:
                buildDailySeries(
                    weekStart,
                    7
                ),

            trend:
                buildTrend(
                    addDays(
                        todayStart,
                        -27
                    ),
                    4,
                    "week"
                ),

            comparison:
                buildWeekComparison(
                    weekStart
                ),

            fixedChargeMonths:
                0
        }),


    month:
        makePeriodData({

            start:
                monthStart,

            end:
                monthEnd,

            previousStart:
                previousMonthStart,

            previousEnd:
                previousMonthEnd,

            mainSeries:
                buildWeeklySeries(
                    monthStart,
                    monthEnd
                ),

            trend:
                buildTrend(
                    addMonths(
                        monthStart,
                        -3
                    ),
                    4,
                    "month"
                ),

            comparison:
                buildMonthComparison(
                    monthStart,
                    monthEnd
                ),

            fixedChargeMonths:
                1
        }),


    "3months":
        makePeriodData({

            start:
                threeMonthStart,

            end:
                threeMonthEnd,

            previousStart:
                previousThreeMonthStart,

            previousEnd:
                previousThreeMonthEnd,

            mainSeries:
                buildMonthlySeries(
                    threeMonthStart,
                    3
                ),

            trend:
                buildTrend(
                    addMonths(
                        monthStart,
                        -5
                    ),
                    6,
                    "month"
                ),

            comparison:
                buildThreeMonthComparison(
                    threeMonthStart
                ),

            fixedChargeMonths:
                3
        })
};