$(document).ready(function() {
    console.log(window.initialData);
    const data = window.initialData;
    const allowAll = window.allowAll;
    // Declare chart instances outside of updateCharts function
    let statusChart, terminalChart, categoryChart, monthlyChart, assigneeChart, resolverChart, unresolvedChart, ticketsTimeChart, slaEscalationChart;

    // =====================================================================
    //  APPEARANCE ONLY — shared look for every chart on this page
    //  (colours match the dashboard and the rest of the system)
    // =====================================================================
    const REDUCED_MOTION = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const FONT = getComputedStyle(document.body).fontFamily || "'Segoe UI', Roboto, sans-serif";
    const UI = { text: '#1b2540', muted: '#6b7489', grid: 'rgba(18, 54, 146, 0.07)' };
    const BRAND = { navy: '#123692', deep: '#172d69', sky: '#4f7be8', red: '#dc3545', redDeep: '#b02a37' };
    const STATUS_COLORS = { open: '#007bff', in_progress: '#c0392b', resolved: '#28a745', closed: '#6c757d', escalated: '#dc9c35' };
    const FALLBACK = ['#123692', '#4f7be8', '#dc9c35', '#17b845', '#c0392b', '#6c757d'];
    const HAS_LABELS = typeof ChartDataLabels !== 'undefined';

    Chart.defaults.font.family = FONT;
    Chart.defaults.color = UI.muted;

    function statusColor(label, i) {
        const key = String(label || '').toLowerCase().trim().replace(/[\s-]+/g, '_');
        return STATUS_COLORS[key] || FALLBACK[i % FALLBACK.length];
    }

    function withAlpha(hex, a) {
        const n = parseInt(hex.replace('#', ''), 16);
        return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
    }

    // Gradient bar fill; the largest bar is highlighted
    function barFill(values, from, to, horizontal = false, highlightTop = true) {
        const max = Math.max(...values.map(v => +v || 0));
        return (ctx) => {
            const { chart, dataIndex } = ctx;
            const area = chart.chartArea;
            const isTop = highlightTop && (+values[dataIndex] || 0) === max && max > 0;
            const [a, b] = isTop ? [BRAND.redDeep, '#f0616f'] : [from, to];
            if (!area) return a;
            const g = horizontal
                ? chart.ctx.createLinearGradient(area.left, 0, area.right, 0)
                : chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
            g.addColorStop(0, a);
            g.addColorStop(1, b);
            return g;
        };
    }

    const tooltipStyle = {
        backgroundColor: '#0f1d4a',
        titleColor: '#ffffff',
        bodyColor: 'rgba(255,255,255,0.88)',
        titleFont: { size: 13, weight: '600', family: FONT },
        bodyFont: { size: 12, family: FONT },
        padding: 12, cornerRadius: 10, caretSize: 6, boxPadding: 5,
        usePointStyle: true,
        borderColor: 'rgba(255,255,255,0.08)', borderWidth: 1,
    };

    const legendBottom = {
        display: true, position: 'bottom',
        labels: { usePointStyle: true, pointStyle: 'circle', boxWidth: 8, boxHeight: 8, padding: 14, color: UI.text, font: { size: 12, weight: '500' } },
    };

    function integerTicks(value) { return Number.isInteger(value) ? value.toLocaleString() : null; }

    function shortLabel(max) {
        return function (value) {
            const label = this.getLabelForValue(value) || '';
            return label.length > max ? label.slice(0, max - 1) + '…' : label;
        };
    }

    function scales({ horizontal = false, labelMax = 16, skip = false } = {}) {
        const valueAxis = {
            beginAtZero: true, grace: '8%',
            border: { display: false },
            grid: { color: UI.grid, drawTicks: false },
            ticks: { color: UI.muted, padding: 8, font: { size: 11 }, callback: integerTicks },
        };
        const categoryAxis = {
            border: { display: false },
            grid: { display: false },
            ticks: { color: UI.muted, padding: 6, font: { size: 11 }, autoSkip: skip, autoSkipPadding: 8, maxRotation: horizontal ? 0 : 40, callback: shortLabel(labelMax) },
        };
        return horizontal ? { x: valueAxis, y: categoryAxis } : { x: categoryAxis, y: valueAxis };
    }

    const valueLabels = {
        anchor: 'end', align: 'end', offset: 2, clamp: true,
        color: UI.text, font: { size: 11, weight: '600' },
        formatter: (v) => (+v > 0 ? (+v).toLocaleString() : ''),
    };

    const sliceLabels = {
        color: '#ffffff',
        font: { size: 11, weight: '700' },
        formatter: (value, ctx) => {
            const total = ctx.dataset.data.reduce((a, b) => a + (+b || 0), 0);
            const pct = total ? (value / total) * 100 : 0;
            return pct >= 6 ? `${Math.round(pct)}%` : '';
        },
    };

    const barMotion = REDUCED_MOTION ? { animation: false } : {
        animation: { duration: 900, easing: 'easeOutQuart', delay: (c) => (c.type === 'data' && c.mode === 'default') ? c.dataIndex * 60 : 0 },
    };
    const donutMotion = REDUCED_MOTION ? { animation: false } : {
        animation: { animateRotate: true, animateScale: true, duration: 1100, easing: 'easeOutQuart' },
    };

    // Number (and caption) in the middle of a doughnut
    function centerText(getText) {
        return {
            id: 'centerText',
            afterDraw(chart) {
                const meta = chart.getDatasetMeta(0);
                if (!meta || !meta.data || !meta.data.length) return;
                const arc = meta.data[0];
                const r = arc.innerRadius;
                if (!r) return;
                const { main, sub } = getText(chart);
                const c = chart.ctx;
                c.save();
                c.textAlign = 'center';
                c.textBaseline = 'middle';
                c.fillStyle = UI.text;
                c.font = `700 ${Math.round(r * 0.38)}px ${FONT}`;
                c.fillText(main, arc.x, arc.y - r * 0.1);
                c.fillStyle = UI.muted;
                c.font = `500 ${Math.max(11, Math.round(r * 0.15))}px ${FONT}`;
                c.fillText(sub, arc.x, arc.y + r * 0.28);
                c.restore();
            },
        };
    }
    const totalCenter = centerText((chart) => ({
        main: chart.data.datasets[0].data.reduce((a, b) => a + (+b || 0), 0).toLocaleString(),
        sub: 'tickets',
    }));

    function pointerCursor(e, elements) { e.native.target.style.cursor = elements.length ? 'pointer' : 'default'; }

    // =====================================================================


    // Initialize the chart rendering with the default data
    updateCharts(data);

    // Function to destroy existing chart if it exists
    function destroyChart(chartInstance) {
        if (chartInstance) {
            chartInstance.destroy();
        }
    }

    // Function to create gradient color
    function createGradient(ctx, chartArea, colorStart, colorEnd) {
        if (!chartArea) return; // Ensure chartArea exists before applying gradient

        let gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        return gradient;
    }

    function updateCharts(data) {
        const ctxStatus = document.getElementById('ticketStatusChart').getContext('2d');
        const ctxTerminal = document.getElementById('ticketsPerTerminalChart').getContext('2d');
        const ctxCategory = document.getElementById('ticketsByCategoryChart').getContext('2d');
        const ctxAssignee = document.getElementById('ticketsByAssigneeChart').getContext('2d');
        const ctxResolver = document.getElementById('ticketsByResolverChart').getContext('2d');
        const ctxUnresolved = document.getElementById('unresolvedTicketsChart').getContext('2d');
        destroyChart(unresolvedChart);
        destroyChart(assigneeChart);


        destroyChart(resolverChart);


        destroyChart(statusChart);
        destroyChart(terminalChart);
        destroyChart(categoryChart);
        destroyChart(monthlyChart);

        const unit = $('#timeUnitFilter').val() || 'day';

        renderTicketsTimeChart(unit, data);
        renderCategoryChart(data);

        $('#timeUnitFilter').on('change', function () {
        const unit = $(this).val();
        renderTicketsTimeChart(unit, data);
    });


    function renderTicketsTimeChart(unit, data) {
        const ctx = document.getElementById("ticketsTimeChart");
        if (!ctx) return;

        const c = ctx.getContext("2d");
        destroyChart(ticketsTimeChart);

        let labels = [];
        let values = [];

        if (unit === "hour") {
            labels = data.ticketsPerHour.labels;
            values = data.ticketsPerHour.data;
        } else if (unit === "day") {
            labels = data.ticketsPerDay.labels;
            values = data.ticketsPerDay.data;
        } else if (unit === "weekday") {
            labels = data.ticketsPerWeekday.labels;
            values = data.ticketsPerWeekday.data;
        } else if (unit === "month") {
            labels = data.ticketsPerMonth.labels;
            values = data.ticketsPerMonth.data;
        } else if (unit === "year") {
            labels = data.ticketsPerYear.labels;
            values = data.ticketsPerYear.data;
        }

        ticketsTimeChart = new Chart(c, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Tickets",
                    data: values,
                    borderColor: BRAND.navy,
                    borderWidth: 2.5,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: BRAND.navy,
                    pointBorderWidth: 2,
                    pointRadius: values.length > 40 ? 0 : 3.5,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: BRAND.navy,
                    backgroundColor: function(context) {
                        const chart = context.chart;
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return null;
                        return createGradient(ctx, chartArea, withAlpha(BRAND.navy, 0.28), withAlpha(BRAND.navy, 0.01));
                    },
                    fill: true,
                    tension: 0.4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                ...(REDUCED_MOTION ? { animation: false } : { animation: { duration: 1000, easing: "easeOutQuart" } }),
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        ...tooltipStyle,
                        callbacks: {
                            label: (ctx) => ` ${ctx.formattedValue} tickets`
                        }
                    }
                },
                scales: scales({ labelMax: 12, skip: true })
            }
        });
    }


        // Ticket statuses chart (doughnut) — status colours as everywhere else
        statusChart = new Chart(ctxStatus, {
            type: 'doughnut',
            data: {
                labels: data.ticketStatuses.labels,
                datasets: [{
                    label: 'Ticket Statuses',
                    data: data.ticketStatuses.data,
                    backgroundColor: data.ticketStatuses.labels.map((l, i) => statusColor(l, i)),
                    borderColor: '#ffffff',
                    borderWidth: 3,
                    hoverOffset: 10,
                    spacing: 2,
                    borderRadius: 6,
                }]
            },
            plugins: [totalCenter, ...(HAS_LABELS ? [ChartDataLabels] : [])],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '64%',
                layout: { padding: 8 },
                ...donutMotion,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        ...tooltipStyle,
                        callbacks: {
                            label(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const value = context.raw;
                                const percent = total ? ((value / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${value} (${percent}%)`;
                            }
                        }
                    },
                    datalabels: sliceLabels
                },
                onHover: pointerCursor
            }
        });

        // Tickets per Terminal Chart
        const terminalCounts = data.ticketsPerTerminal.map(entry => entry.count);
        terminalChart = new Chart(ctxTerminal, {
            type: 'bar',
            data: {
                //labels: data.terminals.map(terminal => terminal.branch_name),
                labels: data.ticketsPerTerminal.map(entry => entry.branch_name),
                datasets: [{
                    label: 'Tickets per Terminal',
                   // data: data.ticketsPerTerminal,
                   data: terminalCounts,
                    backgroundColor: barFill(terminalCounts, BRAND.deep, BRAND.sky),
                    borderRadius: 6,
                    borderSkipped: false,
                    minBarLength: 3,
                    maxBarThickness: 34,
                }]
            },
            plugins: (HAS_LABELS && terminalCounts.length <= 30) ? [ChartDataLabels] : [],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 18 } },
                ...barMotion,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { display: false }, tooltip: tooltipStyle, datalabels: valueLabels },
                scales: scales({ labelMax: 14 })
            }
        });


    function renderCategoryChart(data) {
        // If an existing chart instance exists, destroy it first
        if (categoryChart) {
            categoryChart.destroy();
        }
        // Get the canvas context
        const ctxCategory = document
            .getElementById('ticketsByCategoryChart')
            .getContext('2d');
        const catValues = data.ticketCategories.data;
        // Horizontal bars: category names are long and compare more easily this way
        categoryChart = new Chart(ctxCategory, {
            type: 'bar',
            data: {
            labels: data.ticketCategories.labels,
            datasets: [{
                label: 'Tickets by Category',
                data: catValues,
                backgroundColor: barFill(catValues, BRAND.deep, BRAND.sky, true),
                borderRadius: 6,
                borderSkipped: false,
                minBarLength: 3,
                barPercentage: 0.72,
                maxBarThickness: 26
            }]
            },
            plugins: HAS_LABELS ? [ChartDataLabels] : [],
            options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { right: 28 } },
            ...barMotion,
            hover: {
                onHover: (e, active) => {
                e.native.target.style.cursor = active.length ? 'pointer' : 'default';
                }
            },
            plugins: {
                tooltip: {
                ...tooltipStyle,
                callbacks: {
                    label: ctx => `${ctx.dataset.label}: ${ctx.formattedValue} tickets`
                }
                },
                legend: { display: false },
                datalabels: valueLabels
            },
            scales: scales({ horizontal: true, labelMax: 30 })
            }
        });
        }




       // SLA Chart (Doughnut)
        const ctxSLAEsc = document.getElementById("slaEscalationChart");

        if (ctxSLAEsc && window.initialData.escalationSLAStats) {
            destroyChart(slaEscalationChart);
            const data = window.initialData.escalationSLAStats;
            const ctx = ctxSLAEsc.getContext("2d");

            // Breached & escalated → critical red, breached only → amber, met → green
            const slaColors = ['#e74c3c', '#dc9c35', '#17b845'];

            // Breach percentage in the centre (first slice = breached, as before)
            const centerTextPlugin = centerText((chart) => {
                const dataset = chart.data.datasets[0];
                const total = dataset.data.reduce((a, b) => a + b, 0);
                const breached = dataset.data[0] ?? 0;
                const percent = total ? ((breached / total) * 100).toFixed(1) : 0;
                return { main: `${percent}%`, sub: 'breached' };
            });

            slaEscalationChart = new Chart(ctxSLAEsc, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "SLA Escalation",
                            data: data.data,
                            backgroundColor: data.data.map((_, i) => slaColors[i % slaColors.length]),
                            borderColor: "#fff",
                            borderWidth: 3,
                            hoverOffset: 10,
                            spacing: 2,
                            borderRadius: 6,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "66%",
                    layout: { padding: 8 },
                    ...donutMotion,
                    interaction: {
                        mode: "point",   // precise detection of slices
                        intersect: true, // only fire when pointer is inside slice
                    },
                    plugins: {
                        legend: legendBottom,
                        tooltip: {
                            ...tooltipStyle,
                            callbacks: {
                                label(context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const value = context.raw;
                                    const percent = total ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${context.label}: ${value} (${percent}%)`;
                                },
                            },
                        },
                    },
                },
                plugins: [centerTextPlugin],
            });
        } else {
            console.error("Failed to load SLA data for chart", window.initialData.escalationSLAStats);
        }





        const resolutionCenter = centerText((chart) => {
            const d = chart.data.datasets[0].data;
            const total = d.reduce((a, b) => a + (+b || 0), 0);
            const pct = total ? Math.round(((+d[0] || 0) / total) * 100) : 0;
            return { main: `${pct}%`, sub: 'resolved' };
        });

        unresolvedChart = new Chart(ctxUnresolved, {
            type: 'doughnut',
            data: {
                labels: ['Resolved', 'Unresolved'],
                datasets: [{
                    label: 'Ticket Resolution',
                    data: [data.resolvedTickets, data.unresolvedCount],
                    backgroundColor: ['#17b845', '#e74c3c'],
                    borderColor: '#ffffff',
                    borderWidth: 3,
                    hoverOffset: 10,
                    spacing: 2,
                    borderRadius: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                layout: { padding: 8 },
                ...donutMotion,
                plugins: {
                    legend: legendBottom,
                    tooltip: {
                        ...tooltipStyle,
                        callbacks: {
                            label: function(context) {
                                let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                let value = context.raw;
                                let percent = total ? ((value / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${value} (${percent}%)`;
                            }
                        }
                    },
                    datalabels: { display: false }
                },
                onHover: pointerCursor
            },
            plugins: [resolutionCenter, ...(HAS_LABELS ? [ChartDataLabels] : [])]
        });

        const assigneeValues = data.ticketsByAssignee.data;
        assigneeChart = new Chart(ctxAssignee, {
            type: 'bar',
            data: {
                labels: data.ticketsByAssignee.labels,
                datasets: [{
                    label: 'Tickets Assigned',
                    data: assigneeValues,
                    backgroundColor: barFill(assigneeValues, BRAND.deep, BRAND.sky),
                    borderRadius: 6,
                    borderSkipped: false,
                    minBarLength: 3,
                    maxBarThickness: 36,
                }]
            },
            plugins: HAS_LABELS ? [ChartDataLabels] : [],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 18 } },
                ...barMotion,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: { ...tooltipStyle, enabled: true },
                    datalabels: valueLabels
                },
                scales: scales({ labelMax: 10 })
            }
        });


        // Tickets by Resolver (Bar)
        const resolverValues = data.ticketsByResolver.data;
        resolverChart = new Chart(ctxResolver, {
            type: 'bar',
            data: {
                labels: data.ticketsByResolver.labels,
                datasets: [{
                    label: 'Tickets Resolved',
                    data: resolverValues,
                    backgroundColor: barFill(resolverValues, '#128a35', '#4cd07a', false, false),
                    borderRadius: 6,
                    borderSkipped: false,
                    minBarLength: 3,
                    maxBarThickness: 36,
                }]
            },
            plugins: HAS_LABELS ? [ChartDataLabels] : [],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 18 } },
                ...barMotion,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: tooltipStyle,
                    datalabels: valueLabels
                },
                scales: scales({ labelMax: 10 })
             }
        });

    }

    function updateTicketStatusBreakdown(labels, data) {
        const total = data.reduce((acc, value) => acc + value, 0);
        let breakdownHTML = '';
        labels.forEach((label, index) => {
            const count = data[index];
            const percentage = ((count / total) * 100).toFixed(2);
            const color = statusColor(label, index);
            breakdownHTML += `
              <div class="status-item">
                <div class="status-item-top">
                  <span class="label"><i class="status-dot" style="background:${color}"></i>${label}</span>
                  <span class="value"><strong>${count}</strong> tickets <em>${percentage}%</em></span>
                </div>
                <div class="status-track"><span style="width:${isFinite(percentage) ? percentage : 0}%; background:${color}"></span></div>
              </div>`;
        });
        document.getElementById('ticket-status-breakdown').innerHTML = breakdownHTML;
    }

    // Call the function to display the breakdown
    updateTicketStatusBreakdown(data.ticketStatuses.labels, data.ticketStatuses.data);

    // Populate Dropdowns
    function populateDropdown(id, items, idKey, nameKey, allowAll = true, defaultValue = null, allLabel = "All") {
        const dropdown = document.getElementById(id);
        dropdown.innerHTML = "";

        // Add "All" if allowed, with custom label
        if (allowAll) {
            const allOption = document.createElement("option");
            allOption.value = "all";
            allOption.text = allLabel; // Use custom label
            dropdown.appendChild(allOption);
        }

        // Add the other items
        items.forEach(item => {
            const opt = document.createElement("option");
            opt.value = item[idKey];
            opt.text = item[nameKey];
            dropdown.appendChild(opt);
        });

        // Set default selected value
        if (defaultValue !== null) {
            dropdown.value = defaultValue;
        } else {
            dropdown.value = allowAll ? "all" : (items[0] ? items[0][idKey] : "all");
        }
    }

    // Apply the initial data with proper "All" labels
    if (userGroup === "Internal") {
        populateDropdown("customer-filter", data.customers, "id", "name", true, null, "All Customers");
        populateDropdown("region-filter", data.regions, "id", "name", true, null, "All Regions");
        populateDropdown("terminal-filter", data.terminals, "id", "branch_name", true, null, "All Terminals");
    } else if (userGroup === "Overseer") {
       // Customer is assigned → not changeable
        populateDropdown("customer-filter", data.customers, "id", "name", false, data.assignedCustomerId);

        // Region and Terminal → allow "All" by default
        populateDropdown("region-filter", data.regions, "id", "name", true, "all", "All Regions");
        populateDropdown("terminal-filter", data.terminals, "id", "branch_name", true, "all", "All Terminals");
    } else if (userGroup === "Custodian") {
        populateDropdown("customer-filter", data.customers, "id", "name", false, data.assignedCustomerId);
        populateDropdown("region-filter", data.regions, "id", "name", false, data.assignedRegionId);
        populateDropdown("terminal-filter", data.terminals, "id", "branch_name", false, data.assignedTerminalId);
    }


    // Handle filter changes and update charts dynamically
    $('#time-period, #customer-filter, #terminal-filter, #region-filter').change(function() {
        console.log("Filter changed");
        const timePeriod = $('#time-period').val();
        const customer = $('#customer-filter').val();
        const terminal = $('#terminal-filter').val();
        const region = $('#region-filter').val();

        $.ajax({
            url: '/statistics/',
            type: 'GET',
            data: {
                'time-period': timePeriod,
                'customer': customer,
                'terminal': terminal,
                'region': region,
            },
            success: function(response) {
                console.log("Server response:", response);
                if (response) {
                    try {
                        console.log("New Data:", response);
                        window.initialData = response;
                        updateCharts(response);
                        console.log("Resolved:", response.resolvedTickets, "Unresolved:", response.unresolvedCount);
                    } catch (error) {
                        console.error("Error while updating charts:", error);
                    }
                } else {
                    console.error("No data received from server.");
                }
            },
            error: function(xhr, status, error) {
                console.error("AJAX error:", status, error);
            }
        });
    });

});
