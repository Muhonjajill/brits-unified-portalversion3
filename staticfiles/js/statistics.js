$(document).ready(function() {
    const data = window.initialData;
    const allowAll = window.allowAll;
    // Declare chart instances outside of updateCharts function
    let dayChart, weekdayChart, hourChart, monthChart, yearChart, statusChart, terminalChart, categoryChart, monthlyChart, slaComplianceChart, creatorChart, assigneeChart, resolverChart, unresolvedChart;  

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
        const ctxDay = document.getElementById('ticketsPerDayChart').getContext('2d');
        const ctxWeekday = document.getElementById('ticketsPerWeekdayChart').getContext('2d');
        const ctxHour = document.getElementById('ticketsPerHourChart').getContext('2d');
        const ctxMonth = document.getElementById('ticketsPerMonthChart').getContext('2d');
        const ctxYear = document.getElementById('ticketsPerYearChart').getContext('2d');
        const ctxStatus = document.getElementById('ticketStatusChart').getContext('2d');
        const ctxTerminal = document.getElementById('ticketsPerTerminalChart').getContext('2d');
        const ctxCategory = document.getElementById('ticketsByCategoryChart').getContext('2d');
        const ctxMonthly = document.getElementById('monthlyTicketTrendsChart').getContext('2d');
        const ctxSLA = document.getElementById('slaComplianceChart').getContext('2d');
        const ctxCreator = document.getElementById('ticketsByCreatorChart').getContext('2d');
        const ctxAssignee = document.getElementById('ticketsByAssigneeChart').getContext('2d');
        const ctxResolver = document.getElementById('ticketsByResolverChart').getContext('2d');
        const ctxUnresolved = document.getElementById('unresolvedTicketsChart').getContext('2d');
        destroyChart(unresolvedChart); 
        destroyChart(assigneeChart); 

        // Destroy old charts if exist
        destroyChart(slaComplianceChart);
        destroyChart(creatorChart);
        destroyChart(resolverChart);

        // Destroy the previous charts if they exist
        destroyChart(dayChart);
        destroyChart(weekdayChart);
        destroyChart(hourChart);
        destroyChart(monthChart);
        destroyChart(yearChart);
        destroyChart(statusChart);
        destroyChart(terminalChart);
        destroyChart(categoryChart);
        destroyChart(monthlyChart);

        // Per day chart with gradient animation
        dayChart = new Chart(ctxDay, {
            type: 'bar',
            data: {
                labels: data.days,
                datasets: [{
                    label: 'Tickets per Day',
                    data: data.ticketsPerDay,
                    backgroundColor: function(context) {
                        const chartArea = context.chart.chartArea;
                        return createGradient(ctxDay, chartArea, '#007bff', '#00b0ff');
                    },
                }]
            },
            options: {
                responsive: true,
                animation: {
                    duration: 1000, 
                    easing: 'easeOutQuart',
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0, 123, 255, 0.8)',
                    }
                },
                events: ['resize', 'afterUpdate'], // Ensure chart area is updated
                onResize: function(chart) {
                    chart.update();
                }
            }
        });

        // Per weekday chart with gradient animation
        weekdayChart = new Chart(ctxWeekday, {
            type: 'bar',
            data: {
                labels: data.weekdays,
                datasets: [{
                    label: 'Tickets per Weekday',
                    data: data.ticketsPerWeekday,
                    backgroundColor: function(context) {
                        const chartArea = context.chart.chartArea;
                        return createGradient(ctxWeekday, chartArea, '#28a745', '#32e52f');
                    },
                }]
            },
            options: {
                responsive: true,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    }
                },
                events: ['resize', 'afterUpdate'],
                onResize: function(chart) {
                    chart.update();
                }
            }
        });

        // Per hour chart with gradient animation
        hourChart = new Chart(ctxHour, {
            type: 'bar',
            data: {
                labels: data.hours,
                datasets: [{
                    label: 'Tickets per Hour',
                    data: data.ticketsPerHour,
                    backgroundColor: function(context) {
                        const chartArea = context.chart.chartArea;
                        return createGradient(ctxHour, chartArea, '#ffc107', '#ffcc00');
                    },
                }]
            },
            options: {
                responsive: true,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(255, 193, 7, 0.8)',
                    }
                },
                events: ['resize', 'afterUpdate'],
                onResize: function(chart) {
                    chart.update();
                }
            }
        });

        // Per month chart with gradient animation
        monthChart = new Chart(ctxMonth, {
            type: 'bar',
            data: {
                labels: data.months,
                datasets: [{
                    label: 'Tickets per Month',
                    data: data.ticketsPerMonth,
                    backgroundColor: function(context) {
                        const chartArea = context.chart.chartArea;
                        return createGradient(ctxMonth, chartArea, '#dc3545', '#e02f3a');
                    },
                }]
            },
            options: {
                responsive: true,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    }
                },
                events: ['resize', 'afterUpdate'],
                onResize: function(chart) {
                    chart.update();
                }
            }
        });

        // Per year chart with gradient animation
        yearChart = new Chart(ctxYear, {
            type: 'bar',
            data: {
                labels: data.years,
                datasets: [{
                    label: 'Tickets per Year',
                    data: data.ticketsPerYear,
                    backgroundColor: function(context) {
                        const chartArea = context.chart.chartArea;
                        return createGradient(ctxYear, chartArea, '#17a2b8', '#20c1d7');
                    },
                }]
            },
            options: {
                responsive: true,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(23, 162, 184, 0.8)',
                    }
                },
                events: ['resize', 'afterUpdate'],
                onResize: function(chart) {
                    chart.update();
                }
            }
        });

        // Ticket statuses chart (Pie chart) with hover animations
        statusChart = new Chart(ctxStatus, {
            type: 'pie',
            data: {
                labels: data.ticketStatuses.labels, // Get status labels from data
                datasets: [{
                    label: 'Ticket Statuses',
                    data: data.ticketStatuses.data, // Get status counts from data
                    backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545'],
                }]
            },
            options: {
                responsive: true,
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 1000,
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0, 123, 255, 0.8)',
                    },
                    // Custom Plugin to display the numbers/percentages below the chart
                    datalabels: {
                        display: true,
                        color: '#fff',
                        formatter: (value, context) => {
                            const total = context.chart._metasets[0].data.reduce((acc, val) => acc + val, 0);
                            const percentage = ((value / total) * 100).toFixed(2);  // Calculate percentage
                            return `${value} (${percentage}%)`;  // Format as number and percentage
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
                }
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
                animation: { duration: 1000, easing: 'easeOutQuart' },
            }
        });

        // Tickets by Category (Radar Chart)
        categoryChart = new Chart(ctxCategory, {
            type: 'radar',
            data: {
                labels: data.ticketCategories.labels,
                datasets: [{
                    label: 'Tickets by Category',
                    data: data.ticketCategories.data,
                    backgroundColor: 'rgba(0, 123, 255, 0.3)', 
                    borderColor: '#007bff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                scale: { ticks: { beginAtZero: true } }
            }
        });

        // Monthly Ticket Trends (Line Chart)
        monthlyChart = new Chart(ctxMonthly, {
            type: 'line',
            data: {
                labels: data.months,
                datasets: [{
                    label: 'Monthly Ticket Trends',
                    data: data.ticketsPerMonth,
                    fill: true,
                    backgroundColor: '#007bff',
                    borderColor: '#0056b3',
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                animation: { duration: 1000, easing: 'easeOutQuart' },
                plugins: { tooltip: { backgroundColor: 'rgba(0, 123, 255, 0.8)' } }
            }
        });

        // SLA Chart (Doughnut)
        slaComplianceChart = new Chart(ctxSLA, {
            type: 'doughnut',
            data: {
                labels: data.slaStats.labels,
                datasets: [{
                    label: 'SLA Compliance',
                    data: data.slaStats.data,
                    backgroundColor: ['#28a745', '#dc3545'],
                }]
            },
            options: {
                responsive: true,
                cutout: '70%', // makes the doughnut hollow
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
            plugins: [ChartDataLabels] 
        });

        
        unresolvedChart = new Chart(ctxUnresolved, {
            type: 'doughnut',
            data: {
                labels: ['Resolved', 'Unresolved'],
                datasets: [{
                    label: 'Ticket Resolution',
                    data: [data.resolvedTickets, data.unresolvedTickets], 
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
            plugins: [ChartDataLabels]
        });


        // Tickets by Creator (Bar)
        creatorChart = new Chart(ctxCreator, {
            type: 'bar',
            data: {
                labels: data.ticketsByCreator.labels,
                datasets: [{
                    label: 'Tickets Created',
                    data: data.ticketsByCreator.data,
                    backgroundColor: '#007bff',
                }]
            },
            options: { responsive: true }
        });

        assigneeChart = new Chart(ctxAssignee, {
            type: 'bar',
            data: {
                labels: data.ticketsByAssignee.labels,
                datasets: [{
                    label: 'Tickets Assigned',
                    data: data.ticketsByAssignee.data,
                    backgroundColor: data.ticketsByAssignee.labels.map((_, i) => {
                        // Assign distinct colors from a palette
                        const colors = [
                            '#007bff', '#28a745', '#ffc107', '#dc3545',
                            '#17a2b8', '#6f42c1', '#fd7e14', '#20c997'
                        ];
                        return colors[i % colors.length]; // cycle through
                    }),
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: { enabled: true }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
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
            options: { responsive: true }
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
        //populateDropdown("customer-filter", data.customers, "id", "name", false, data.assignedCustomerId);
        //populateDropdown("region-filter", data.regions, "id", "name", false, "all", "All Regions");
       // populateDropdown("terminal-filter", data.terminals, "id", "branch_name", false, "all", "All Terminals");

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
                        updateCharts(response); 
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
