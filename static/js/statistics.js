$(document).ready(function() {
    console.log(window.initialData);
    const data = window.initialData;
    const allowAll = window.allowAll;
    // Declare chart instances outside of updateCharts function
    let statusChart, terminalChart, categoryChart, monthlyChart, assigneeChart, resolverChart, unresolvedChart, ticketsTimeChart, slaEscalationChart;  


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
                    borderColor: "#007bff",
                    pointBackgroundColor: "#007bff",
                    borderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 8,
                    backgroundColor: function(context) {
                        const chart = context.chart;
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return null;
                        return createGradient(ctx, chartArea, "rgba(0,123,255,0.5)", "rgba(0,123,255,0)");
                    },
                    fill: true,
                    tension: 0.4,
                }]
            },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                animation: { duration: 1500, easing: "easeOutBounce" },
                plugins: {
                    legend: { display: true, labels: { color: "#333", font: { size: 14, weight: 'bold' } } },
                    tooltip: {
                        backgroundColor: "rgba(0,0,0,0.7)",
                        titleFont: { size: 14, weight: "bold" },
                        bodyFont: { size: 13 },
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => ` ${ctx.formattedValue} tickets`
                        }
                    }
                },
                elements: {
                    line: { borderJoinStyle: "round", shadowBlur: 8, shadowColor: "rgba(0,0,0,0.15)" },
                    point: { hoverBorderWidth: 3 }
                }
            }
        });
    }


        // Ticket statuses chart (Pie chart) with hover animations
        statusChart = new Chart(ctxStatus, {
            type: 'pie',
            data: {
                labels: data.ticketStatuses.labels, 
                datasets: [{
                    label: 'Ticket Statuses',
                    data: data.ticketStatuses.data,
                    backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545'],
                }]
            },
            options: {
                responsive: true,
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 1200,
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0, 123, 255, 0.8)',
                    },
                    datalabels: {
                        display: true,
                        color: '#fff',
                        formatter: (value, context) => {
                            const total = context.chart._metasets[0].data.reduce((acc, val) => acc + val, 0);
                            const percentage = ((value / total) * 100).toFixed(2);  
                            return `${value} (${percentage}%)`;  
                        },
                        font: {
                            weight: 'bold',
                            size: 14
                        },
                        anchor: 'end',
                        align: 'center',
                        offset: 10
                    }
                },
                events: ['resize', 'afterUpdate'],
                onResize: function(chart) {
                    chart.update();
                },
                hover: { mode: 'nearest', onHover: (e, elements) => e.native.target.style.cursor = elements.length ? 'pointer' : 'default'} 
            }
        });

        // Tickets per Terminal Chart
        terminalChart = new Chart(ctxTerminal, {
            type: 'bar',
            data: {
                //labels: data.terminals.map(terminal => terminal.branch_name),
                labels: data.ticketsPerTerminal.map(entry => entry.branch_name),
                datasets: [{
                    label: 'Tickets per Terminal',
                   // data: data.ticketsPerTerminal,
                   data: data.ticketsPerTerminal.map(entry => entry.count),
                    backgroundColor: function(context) {
                        const chartArea = context.chart.chartArea;
                        return createGradient(ctxTerminal, chartArea, '#007bff', '#00b0ff');
                    },
                }]
            },
            options: {
                responsive: true,
                animation: { duration: 1200, easing: 'easeOutQuart', delay: (context) => context.dataIndex * 100 },
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
        categoryChart = new Chart(ctxCategory, {
            type: 'radar',
            data: {
            labels: data.ticketCategories.labels,
            datasets: [{
                label: 'Tickets by Category',
                data: data.ticketCategories.data,
                backgroundColor: context => {
                const { chartArea } = context.chart;
                return createGradient(
                    ctxCategory,
                    chartArea,
                    'rgba(0, 123, 255, 0.3)',
                    'rgba(0, 123, 255, 0.1)'
                );
                },
                borderColor: context => {
                const v = context.dataset.data[context.dataIndex];
                return v > 10 ? '#ff4500' : '#007bff';
                },
                borderWidth: 2,
                pointBackgroundColor: context => {
                const v = context.dataset.data[context.dataIndex];
                return v > 10 ? '#ff4500' : '#007bff';
                },
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8,
                pointHoverBackgroundColor: context => {
                const v = context.dataset.data[context.dataIndex];
                return v > 10 ? '#ff6347' : '#007bff';
                },
                pointHoverBorderWidth: 2,
                fill: true
            }]
            },
            options: {
            responsive: true,
            scale: {
                ticks: {
                beginAtZero: true,
                backdropColor: 'rgba(0, 0, 0, 0.1)',
                color: '#333',
                font: { size: 14 }
                },
                pointLabels: {
                color: '#007bff',
                font: { size: 14, weight: 'bold' }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeOutBounce',
                onComplete: function(anim) {
                const chart = anim.chart;
                const ctx   = chart.ctx;
                if (!ctx) return;
                ctx.save();
                ctx.globalAlpha = 0.5;
                chart.data.datasets.forEach((ds, idx) => {
                    ctx.fillStyle = ds.borderColor;
                    ds.data.forEach((_, i) => {
                    const pt = chart.getDatasetMeta(idx).data[i];
                    ctx.beginPath();
                    ctx.arc(pt.x, pt.y, 6, 0, 2 * Math.PI);
                    ctx.fill();
                    });
                });
                ctx.restore();
                }
            },
            hover: {
                onHover: (e, active) => {
                e.native.target.style.cursor = active.length ? 'pointer' : 'default';
                }
            },
            plugins: {
                tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                titleFont: { size: 14, weight: 'bold' },
                bodyFont: { size: 12 },
                padding: 10,
                cornerRadius: 6,
                callbacks: {
                    label: ctx => `${ctx.dataset.label}: ${ctx.formattedValue} tickets`
                }
                },
                legend: {
                display: true,
                labels: {
                    color: '#333',
                    font: { size: 14, weight: 'bold' }
                }
                }
            }
            }
        });
        }


      

       // SLA Chart (Doughnut)
        const ctxSLAEsc = document.getElementById("slaEscalationChart");

        if (ctxSLAEsc && window.initialData.escalationSLAStats) {
            destroyChart(slaEscalationChart); 
            const data = window.initialData.escalationSLAStats;
            const ctx = ctxSLAEsc.getContext("2d");

            // --- Gradients for each slice ---
            // Softer, modern gradients
            const gradBreachedEsc = ctx.createLinearGradient(0, 0, 0, 300);
            gradBreachedEsc.addColorStop(0, "#FF7E67");  // warm coral
            gradBreachedEsc.addColorStop(1, "#FF3C38");  // soft red

            const gradBreachedNoEsc = ctx.createLinearGradient(0, 0, 0, 300);
            gradBreachedNoEsc.addColorStop(0, "#6DD5FA"); // aqua blue
            gradBreachedNoEsc.addColorStop(1, "#2980B9"); // calm teal

            const gradMet = ctx.createLinearGradient(0, 0, 0, 300);
            gradMet.addColorStop(0, "#A5E1CE");  // soft mint
            gradMet.addColorStop(1, "#2E8B57");  // deeper sea-gree

            // Custom plugin for center percentage text
            const centerTextPlugin = {
                id: "centerText",
                afterDraw(chart) {
                    const { ctx, chartArea } = chart;
                    const dataset = chart.data.datasets[0];
                    const total = dataset.data.reduce((a, b) => a + b, 0);
                    const breached = dataset.data[0] ?? 0;
                    const percent = total ? ((breached / total) * 100).toFixed(1) : 0;

                    ctx.save();
                    ctx.font = "bold 20px 'Segoe UI', sans-serif";
                    ctx.fillStyle = "#444";
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillText(`${percent}%`, (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2);
                    ctx.restore();
                },
            };

            slaEscalationChart = new Chart(ctxSLAEsc, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "SLA Escalation",
                            data: data.data,
                            backgroundColor: [gradBreachedEsc, gradBreachedNoEsc, gradMet],
                            borderColor: "#fff",
                            borderWidth: 2,
                            hoverOffset: 12,
                            hitRadius: 4,
                            shadowColor: "rgba(0,0,0,0.15)",
                            shadowBlur: 8,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    cutout: "68%",
                    animation: {
                        animateRotate: true,
                        animateScale: true,
                        duration: 1800,
                        easing: "easeOutElastic",
                    },
                    interaction: {
                        mode: "point",   // precise detection of slices
                        intersect: true, // only fire when pointer is inside slice
                    },
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                usePointStyle: true,
                                pointStyle: "circle",
                                font: { size: 14, weight: "bold" },
                                color: "#333",
                                padding: 14,
                            },
                        },
                        tooltip: {
                            backgroundColor: "#222",
                            titleFont: { size: 14, weight: "bold" },
                            bodyFont: { size: 13 },
                            padding: 12,
                            cornerRadius: 6,
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




        
        unresolvedChart = new Chart(ctxUnresolved, {
            type: 'doughnut',
            data: {
                labels: ['Resolved', 'Unresolved'],
                datasets: [{
                    label: 'Ticket Resolution',
                    data: [data.resolvedTickets, data.unresolvedCount], 
                    backgroundColor: ['#28a745', '#dc3545'],
                }]
            },
            options: {
                responsive: true,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                let value = context.raw;
                                let percent = total ? ((value / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${value} (${percent}%)`;
                            }
                        }
                    },
                    datalabels: {
                        color: '#fff',
                        formatter: (value, ctx) => {
                            let total = ctx.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                            return total ? ((value / total) * 100).toFixed(1) + '%' : '0%';
                        },
                        font: {
                            weight: 'bold',
                            size: 14
                        }
                    }
                }
            },
            animation: { animateRotate: true, animateScale: true, duration: 1200 },
            hover: { mode: 'nearest', onHover: (e, elements) => e.native.target.style.cursor = elements.length ? 'pointer' : 'default' },
            plugins: [ChartDataLabels]
        });

        assigneeChart = new Chart(ctxAssignee, {
            type: 'bar',
            data: {
                labels: data.ticketsByAssignee.labels,
                datasets: [{
                    label: 'Tickets Assigned',
                    data: data.ticketsByAssignee.data,
                    backgroundColor: data.ticketsByAssignee.labels.map((_, i) => {
                        const colors = [
                            '#007bff', '#28a745', '#ffc107', '#dc3545',
                            '#17a2b8', '#6f42c1', '#fd7e14', '#20c997'
                        ];
                        return colors[i % colors.length]; 
                    }),
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: { enabled: true }
                },
                animation: {
                    duration: 1200,
                    easing: 'easeOutQuart',
                    delay: (context) => context.dataIndex * 100 
                }
            }
        });


        // Tickets by Resolver (Bar)
        resolverChart = new Chart(ctxResolver, {
            type: 'bar',
            data: {
                labels: data.ticketsByResolver.labels,
                datasets: [{
                    label: 'Tickets Resolved',
                    data: data.ticketsByResolver.data,
                    backgroundColor: '#17a2b8',
                }]
            },
            options: { responsive: true,
                animation: {
                    duration: 1200,
                    easing: 'easeOutQuart',
                    delay: (context) => context.dataIndex * 100 
                }
             }
        });

    }

    function updateTicketStatusBreakdown(labels, data) {
        const total = data.reduce((acc, value) => acc + value, 0);
        let breakdownHTML = '';
        labels.forEach((label, index) => {
            const count = data[index];
            const percentage = ((count / total) * 100).toFixed(2);
            breakdownHTML += `<p><strong>${label}:</strong> ${count} tickets (${percentage}%)</p>`;
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
