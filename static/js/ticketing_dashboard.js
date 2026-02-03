window.addEventListener('DOMContentLoaded', () => {
  const userProfile = document.getElementById("userProfile");
  if (userProfile) {
    const profileTrigger = userProfile.querySelector(".profile-trigger");
    const dropdownMenu = userProfile.querySelector(".dropdown-menu");

    // Toggle dropdown visibility
    profileTrigger.addEventListener("click", () => {
      dropdownMenu.classList.toggle("show");
    });

    document.addEventListener("click", (e) => {
    if (!userProfile.contains(e.target)) {
      dropdownMenu.classList.remove("show");
    }
  });
  }



  // === Hamburger menu toggle ===
  const dashboardHamburger = document.getElementById('hamburger');
  const dashboardSidebar = document.getElementById('sidebar');
  if (dashboardHamburger && dashboardSidebar) {
    dashboardHamburger.addEventListener('click', function () {
      dashboardSidebar.classList.toggle('active');
    });
    document.addEventListener('click', function (event) {
      if (dashboardSidebar.classList.contains('active') &&
          !dashboardSidebar.contains(event.target) &&
          !dashboardHamburger.contains(event.target)) {
        dashboardSidebar.classList.remove('active');
      }
    });
  }

  // === Search Filter Function (targets dashboard cards) ===
  const searchInput = document.getElementById('navbarSearchInput');
  if (searchInput) {
    searchInput.addEventListener('keyup', function () {
      const query = this.value.toLowerCase().trim();
      const cards = document.querySelectorAll('.dashboard-grid .card');
      cards.forEach(card => {
        const title = card.querySelector('.card-title')?.innerText.toLowerCase();
        card.style.display = title?.includes(query) ? '' : 'none';
      });
    });
  }

  // === Global Color Mapping 
  const COLOR_MAP = {
    primary: '#007ACC',           
    secondary: '#FF8C00',          

    // Status/Categorization Colors
    success: '#4CAF50',            
    warning: '#FFC107',           
    danger: '#DC3545',            
    info: '#17A2B8', 
    
    low: '#17b845',            
    medium: '#007bff',           
    high: '#dc9c35',            
    critical: '#e74c3c',     
    
    open: '#007bff',
    in_progress: '#c0392b',
    closed: 'rgb(25, 164, 25)',

    // Neutral/Supporting Colors
    neutralDark: '#34495E',        
    neutralLight: '#ECF0F1',      
    textDark: '#2C3E50',          
    textLight: '#7F8C8D',         

    // Lighter Tones for Backgrounds/Fills
    primaryLight: 'rgba(0, 122, 204, 0.15)',  
    infoLight: 'rgba(23, 162, 184, 0.15)',    

    // Gradient Set for diverse categories or multi-series charts
    gradientSet: [
      '#007ACC', 
      '#673AB7', 
      '#FF8C00', 
      '#00BCD4', 
      '#8BC34A', 
      '#FF5722', 
      '#9C27B0', 
      '#FFD700'  
    ],

    // Specific Use Case Colors
    terminalRegionBase: '#4A6572' 
  };

  // === Enhanced Chart Animation and Styling Config ===
  const animationOptions = {
    animation: {
      duration: 1500, // Smooth, professional animation duration
      easing: 'easeInOutCubic', // Sophisticated easing for smooth transitions
      delay: (context) => {
        // Staggered animation for bar/line charts
        let delay = 0;
        if (context.type === 'data' && context.mode === 'default') {
          delay = context.dataIndex * 80 + context.datasetIndex * 100;
        }
        return delay;
      },
      onProgress: function(animation) {
        // Optional: Track animation progress
        const progress = animation.currentStep / animation.numSteps;
        // Can be used for custom loading indicators
      },
      onComplete: function (animation) {
        // Subtle completion callback
        const chart = animation.chart;
        chart.options.animation.duration = 300; // Faster updates after initial render
      }
    },
    animations: {
      // Enhanced property-specific animations
      tension: {
        duration: 1000,
        easing: 'easeInOutCubic',
        from: 0.3,
        to: 0.4,
        loop: false
      },
      radius: {
        duration: 800,
        easing: 'easeOutElastic',
        from: 0,
        to: 5
      },
      borderWidth: {
        duration: 600,
        easing: 'easeInOutQuad'
      }
    },
    transitions: {
      // Smooth transitions on data updates
      active: {
        animation: {
          duration: 400,
          easing: 'easeInOutQuart'
        }
      },
      resize: {
        animation: {
          duration: 500,
          easing: 'easeInOutQuad'
        }
      },
      show: {
        animations: {
          x: {
            from: 0
          },
          y: {
            from: 0
          }
        }
      },
      hide: {
        animations: {
          x: {
            to: 0
          },
          y: {
            to: 0
          }
        }
      }
    },
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
      animationDuration: 200 // Quick hover response
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          boxWidth: 15,
          padding: 20,
          font: {
            size: 14,
            family: 'Roboto, sans-serif',
            weight: '500'
          },
          color: COLOR_MAP.textDark,
          usePointStyle: true, // Rounded legend markers
          pointStyle: 'circle'
        },
        onHover: function(event, legendItem, legend) {
          event.native.target.style.cursor = 'pointer';
        },
        onLeave: function(event, legendItem, legend) {
          event.native.target.style.cursor = 'default';
        }
      },
      tooltip: {
        enabled: true,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        titleFont: {
          size: 15,
          weight: 'bold',
          family: 'Roboto, sans-serif',
        },
        bodyFont: {
          size: 13,
          family: 'Roboto, sans-serif',
        },
        footerFont: {
          size: 11,
          family: 'Roboto, sans-serif',
          style: 'italic'
        },
        padding: 14,
        caretPadding: 12,
        caretSize: 6,
        cornerRadius: 10,
        displayColors: true,
        borderColor: COLOR_MAP.primary,
        borderWidth: 2,
        boxPadding: 6,
        usePointStyle: true,
        callbacks: {
          // Enhanced tooltip with animations
          title: function(context) {
            return context[0].label || '';
          },
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y;
            }
            return label;
          }
        },
        animation: {
          duration: 300,
          easing: 'easeOutQuart'
        }
      },
      // Subtle animation on hover
      decimation: {
        enabled: false
      }
    },
    hover: {
      mode: 'nearest',
      intersect: true,
      animationDuration: 300,
      onHover: function(event, activeElements) {
        event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
      }
    },
    scales: {
      x: {
        ticks: {
          color: COLOR_MAP.textLight,
          font: {
            family: 'Roboto, sans-serif',
            size: 12
          },
          maxRotation: 45,
          minRotation: 0
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
          borderColor: COLOR_MAP.neutralLight,
          lineWidth: 1,
          drawBorder: true,
          drawOnChartArea: true,
          drawTicks: true,
          tickLength: 8,
          offset: true
        },
        border: {
          display: true,
          color: COLOR_MAP.neutralLight,
          width: 2
        }
      },
      y: {
        ticks: {
          color: COLOR_MAP.textLight,
          font: {
            family: 'Roboto, sans-serif',
            size: 12
          },
          callback: function(value) {
            return Number.isInteger(value) ? value : null; // Only show integer ticks
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.08)',
          borderColor: COLOR_MAP.neutralLight,
          lineWidth: 1,
          drawBorder: true,
          drawOnChartArea: true,
          drawTicks: true,
          tickLength: 8
        },
        border: {
          display: true,
          color: COLOR_MAP.neutralLight,
          width: 2
        }
      }
    },
    // Element-specific hover effects
    elements: {
      point: {
        radius: 4,
        hoverRadius: 7,
        hitRadius: 10,
        borderWidth: 2,
        hoverBorderWidth: 3
      },
      line: {
        borderWidth: 3,
        tension: 0.4,
        borderCapStyle: 'round',
        borderJoinStyle: 'round'
      },
      bar: {
        borderWidth: 0,
        borderRadius: 6,
        borderSkipped: false
      },
      arc: {
        borderWidth: 2,
        hoverBorderWidth: 3,
        hoverOffset: 8 // Pie slice pop-out on hover
      }
    }
  };

  // === Initialize Charts ===
  // Helper function to safely destroy existing chart
  function destroyExistingChart(canvasId) {
    const chartInstance = Chart.getChart(canvasId);
    if (chartInstance) {
      chartInstance.destroy();
    }
  }

   // Handle KPI clicks
    const kpiCards = document.querySelectorAll('.kpi-card');

    kpiCards.forEach(card => {
        card.addEventListener('click', function() {
            const period = card.getAttribute('data-period'); 
            window.location.href = `/tickets/${period}/`; 
        });
    });


  // Modal functionality for displaying tickets
  function createTicketModal() {
    // Check if modal already exists
    if (document.getElementById('ticketModal')) {
      return document.getElementById('ticketModal');
    }

    const modal = document.createElement('div');
    modal.id = 'ticketModal';
    modal.className = 'ticket-modal';
    modal.innerHTML = `
      <div class="modal-overlay"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h2 class="modal-title"></h2>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="modal-loading">
            <div class="spinner"></div>
            <p>Loading tickets...</p>
          </div>
          <div class="modal-tickets"></div>
          <div class="modal-empty" style="display: none;">
            <i class="fas fa-inbox"></i>
            <p>No tickets found</p>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    // Close modal handlers
    const closeBtn = modal.querySelector('.modal-close');
    const overlay = modal.querySelector('.modal-overlay');
    
    closeBtn.addEventListener('click', () => closeModal());
    overlay.addEventListener('click', () => closeModal());
    
    // ESC key to close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.classList.contains('active')) {
        closeModal();
      }
    });

    return modal;
  }

  /*function showModal(title, tickets) {
    const modal = createTicketModal();
    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('.modal-tickets');
    const loadingEl = modal.querySelector('.modal-loading');
    const emptyEl = modal.querySelector('.modal-empty');

    modalTitle.textContent = title;
    modalBody.innerHTML = '';
    loadingEl.style.display = 'none';
    emptyEl.style.display = 'none';

    if (!tickets || tickets.length === 0) {
      emptyEl.style.display = 'flex';
    } else {
      tickets.forEach((ticket, index) => {
        const ticketCard = document.createElement('div');
        ticketCard.className = 'ticket-card';
        ticketCard.style.animationDelay = `${index * 0.05}s`;
        
        const statusClass = ticket.status ? ticket.status.toLowerCase().replace(' ', '_') : 'unknown';
        const priorityClass = ticket.priority ? ticket.priority.toLowerCase() : 'unknown';
        
        ticketCard.innerHTML = `
          <div class="ticket-card-header">
            <div class="ticket-id">#${ticket.id || 'N/A'}</div>
            <div class="ticket-badges">
              <span class="badge badge-status status-${statusClass}">${ticket.status || 'Unknown'}</span>
              <span class="badge badge-priority priority-${priorityClass}">${ticket.priority || 'Unknown'}</span>
            </div>
          </div>
          <h3 class="ticket-title">${ticket.title || 'Untitled'}</h3>
          <div class="ticket-meta">
            <div class="meta-item">
              <i class="fas fa-user"></i>
              <span>${ticket.created_by || 'Unknown'}</span>
            </div>
            <div class="meta-item">
              <i class="fas fa-calendar"></i>
              <span>${ticket.created_at || 'N/A'}</span>
            </div>
            ${ticket.assigned_to ? `
            <div class="meta-item">
              <i class="fas fa-user-tag"></i>
              <span>${ticket.assigned_to}</span>
            </div>
            ` : ''}
          </div>
          <div class="ticket-actions">
            <a href="/tickets/${ticket.id}/" class="btn-view">
              <i class="fas fa-eye"></i> View Details
            </a>
          </div>
        `;
        modalBody.appendChild(ticketCard);
      });
    }

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }*/

  function closeModal() {
    const modal = document.getElementById('ticketModal');
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  // Fetch tickets from server and show in modal
  function fetchAndShowTickets(endpoint, title) {
    const modal = createTicketModal();
    const loadingEl = modal.querySelector('.modal-loading');
    const modalBody = modal.querySelector('.modal-tickets');
    const emptyEl = modal.querySelector('.modal-empty');
    const modalTitle = modal.querySelector('.modal-title');

    modalTitle.textContent = title;
    modalBody.innerHTML = '';
    loadingEl.style.display = 'flex';
    emptyEl.style.display = 'none';
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    fetch(endpoint)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        loadingEl.style.display = 'none';
        const tickets = data.tickets || [];
        const timeData = data.time_data || {};

        // Show totals
        document.getElementById("dailyCount").textContent = timeData.day;
        document.getElementById("weeklyCount").textContent = timeData.week;
        document.getElementById("monthlyCount").textContent = timeData.month;
        document.getElementById("yearlyCount").textContent = timeData.year;

        if (tickets.length === 0) {
          emptyEl.style.display = 'flex';
        } else {
          renderTicketsTable(tickets);
        }
      })
      .catch(error => {
        console.error('Error fetching tickets:', error);
        loadingEl.style.display = 'none';
        emptyEl.innerHTML = `
          <i class="fas fa-exclamation-triangle"></i>
          <p>Error loading tickets</p>
          <small>${error.message}</small>
        `;
        emptyEl.style.display = 'flex';
      });
  }

  const ticketReportChart = document.getElementById('ticketReportChart');
  if (ticketReportChart) {
    destroyExistingChart('ticketReportChart');
    const statusLabels = STATUS_DATA.map(item => item.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()));
    const statusCounts = STATUS_DATA.map(item => item.count);
    new Chart(ticketReportChart, {
      type: 'bar',
      data: {
        labels: statusLabels,
        datasets: [{
          label: 'Tickets',
          data: statusCounts,
          backgroundColor: [COLOR_MAP.primary, COLOR_MAP.warning, COLOR_MAP.success, COLOR_MAP.danger],
          borderRadius: 5,
          barThickness: 40
        }]
      },
      options: {
        ...animationOptions,
        scales: {
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1 },
            grid: { drawBorder: false }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });
  }

  const monthlyTrendChart = document.getElementById('monthlyTrendChart');
  if (monthlyTrendChart) {
    destroyExistingChart('monthlyTrendChart');
    const monthlyLabels = MONTHLY_DATA.map(item => item.month);
    const monthlyCounts = MONTHLY_DATA.map(item => item.count);
    new Chart(monthlyTrendChart, {
      type: 'line',
      data: {
        labels: monthlyLabels,
        datasets: [{
          label: 'Tickets',
          data: monthlyCounts,
          borderColor: '#123692',
          backgroundColor: 'rgba(18, 54, 146, 0.1)',
          tension: 0.4,
          fill: true,
          pointBackgroundColor: '#123692',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointHoverBackgroundColor: '#172d69',
          pointHoverBorderWidth: 3
        }]
      },
      options: {
        ...animationOptions,
        scales: {
          ...animationOptions.scales,
          y: {
            ...animationOptions.scales.y,
            beginAtZero: true
          }
        }
      }
    });
  }

  const terminalChart = document.getElementById('terminalChart');
  if (terminalChart) {
    destroyExistingChart('terminalChart');
    const terminalLabels = TERMINAL_DATA.map(item => item.terminal || 'Unnamed');
    const terminalCounts = TERMINAL_DATA.map(item => item.count);
    const terminalIds = TERMINAL_DATA.map(item => item.terminal_id);
    
    new Chart(terminalChart, {
      type: 'bar',
      data: {
        labels: terminalLabels,
        datasets: [{
          label: 'Tickets',
          data: terminalCounts,
          backgroundColor: terminalLabels.map((_, i) => {
            const colors = ['#123692', '#172d69', '#dc3545'];
            return colors[i % colors.length];
          }),
          borderRadius: 8,
          barThickness: 35,
          hoverBackgroundColor: terminalLabels.map((_, i) => {
            const colors = ['#172d69', '#123692', '#b02a37'];
            return colors[i % colors.length];
          })
        }]
      },
      options: {
        ...animationOptions,
        scales: {
          ...animationOptions.scales,
          y: {
            ...animationOptions.scales.y,
            beginAtZero: true
          },
          x: {
            ...animationOptions.scales.x,
            grid: { display: false }
          }
        },
        onClick: (event) => {
          const chart = event.chart;

          const points = chart.getElementsAtEventForMode(
            event.native,
            'nearest',
            { intersect: true },
            true
          );

          if (!points.length) return;

          const index = points[0].index;
          const terminalId = terminalIds[index];
          const terminalName = terminalLabels[index];

          console.log('Clicked terminal:', terminalName, terminalId);

          if (!terminalId) return;

          fetchAndShowTickets(
            `/api/tickets/?terminal=${terminalId}`,
            `Tickets for ${terminalName}`
          );
        }
      }
    });
  }

  // === Region-wise Ticket Volume ===
  const regionChart = document.getElementById('regionChart');
  if (regionChart) {
    destroyExistingChart('regionChart');
    const regionLabels = REGION_DATA.map(item => item.region || 'Unnamed');
    const regionCounts = REGION_DATA.map(item => item.count);
    
    new Chart(regionChart, {
      type: 'bar',
      data: {
        labels: regionLabels,
        datasets: [{
          label: 'Tickets',
          data: regionCounts,
          backgroundColor: regionLabels.map((_, i) => {
            const colors = ['#123692', '#172d69', '#dc3545', '#123692', '#172d69'];
            return colors[i % colors.length];
          }),
          borderRadius: 8,
          barThickness: 35,
          hoverBackgroundColor: regionLabels.map((_, i) => {
            const colors = ['#172d69', '#123692', '#b02a37', '#172d69', '#123692'];
            return colors[i % colors.length];
          })
        }]
      },
      options: {
        ...animationOptions,
        scales: {
          ...animationOptions.scales,
          y: {
            ...animationOptions.scales.y,
            beginAtZero: true
          }
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const region = regionLabels[index];
            fetchAndShowTickets(`/api/tickets/?region=${encodeURIComponent(region)}`, `Tickets in ${region}`);
          }
        }
      }
    });
  }

  const priorityChart = document.getElementById('priorityChart');
    if (priorityChart) {
      destroyExistingChart('priorityChart');
      const priorityData = PRIORITY_DATA.map(item => ({
        priority: item.priority,
        count: item.count
      }));
      const priorityLabels = priorityData.map(item => item.priority.charAt(0).toUpperCase() + item.priority.slice(1));
      const priorityCounts = priorityData.map(item => item.count);
      
      const priorityChartInstance = new Chart(priorityChart, {
        type: 'pie',
        data: {
          labels: priorityLabels,
          datasets: [{
            data: priorityCounts,
            backgroundColor: priorityData.map(item => {
              const p = item.priority.toLowerCase();
              if (p === 'low') return '#17b845';
              if (p === 'medium') return '#007bff';
              if (p === 'high') return '#dc9c35';
              if (p === 'critical') return '#e74c3c';
              return '#6c757d';
            }),
            borderColor: '#fff',
            borderWidth: 3,
            hoverBorderWidth: 4,
            hoverOffset: 12
          }]
        },
        options: {
          ...animationOptions,
          onClick: (event, elements) => {
            if (elements.length > 0) {
              const index = elements[0].index;
              const priority = priorityData[index].priority;
              const priorityLabel = priorityLabels[index];
              fetchAndShowTickets(`/api/tickets/?priority=${priority}`, `${priorityLabel} Priority Tickets`)
            }
          },
          plugins: {
            ...animationOptions.plugins,
            tooltip: {
              ...animationOptions.plugins.tooltip,
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.parsed || 0;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = ((value / total) * 100).toFixed(1);
                  return `${label}: ${value} (${percentage}%)`;
                }
              }
            }
          }
        }
      });
    }

    const statusChart = document.getElementById('statusChart');
    if (statusChart) {
      destroyExistingChart('statusChart');
      const statusData = STATUS_DATA.map(item => ({
        status: item.status,
        count: item.count
      }));
      const statusLabels = statusData.map(item => item.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()));
      const statusCounts = statusData.map(item => item.count);
      
      const statusChartInstance = new Chart(statusChart, {
        type: 'pie',
        data: {
          labels: statusLabels,
          datasets: [{
            data: statusCounts,
            backgroundColor: statusData.map(item => {
              const s = item.status.toLowerCase().replace(' ', '_');
              if (s === 'open') return '#007bff';
              if (s === 'in_progress') return '#c0392b';
              if (s === 'resolved') return '#28a745';
              if (s === 'closed') return '#6c757d';
              return '#cccccc';
            }),
            borderColor: '#fff',
            borderWidth: 3,
            hoverBorderWidth: 4,
            hoverOffset: 12
          }]
        },
        options: {
          ...animationOptions,
          onClick: (event, elements) => {
            if (elements.length > 0) {
              const index = elements[0].index;
              const status = statusData[index].status;
              const statusLabel = statusLabels[index];
              fetchAndShowTickets(`/api/tickets/?status=${status}`, `${statusLabel} Tickets`);
            }
          },
          plugins: {
            ...animationOptions.plugins,
            tooltip: {
              ...animationOptions.plugins.tooltip,
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.parsed || 0;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = ((value / total) * 100).toFixed(1);
                  return `${label}: ${value} (${percentage}%)`;
                }
              }
            }
          }
        }
      });
    }
    
  const timeTrendChart = document.getElementById('timeTrendChart');
  if (timeTrendChart) {
    destroyExistingChart('timeTrendChart');
    new Chart(timeTrendChart, {
      type: 'line',
      data: {
        labels: ['Day', 'Week', 'Month', 'Year'],
        datasets: [{
          label: 'Ticket Volume',
          data: [TIME_DATA.day, TIME_DATA.week, TIME_DATA.month, TIME_DATA.year],
          borderColor: '#172d69',
          backgroundColor: 'rgba(23, 45, 105, 0.1)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#172d69',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointHoverBackgroundColor: '#123692',
          pointHoverBorderWidth: 3
        }]
      },
      options: animationOptions
    });
  }

  const categoryChart = document.getElementById('categoryChart');
  if (categoryChart) {
    destroyExistingChart('categoryChart');
    new Chart(categoryChart, {
      type: 'bar',
      data: {
        labels: CATEGORY_DATA.map(c => c.category),
        datasets: [{
          label: 'Tickets',
          data: CATEGORY_DATA.map(c => c.count),
          backgroundColor: COLOR_MAP.gradientSet[1],
          borderRadius: 4,
          barThickness: 30
        }]
      },
      options: animationOptions
    });
  }

  const categoryTimeChart = document.getElementById('categoryTimeChart');
  if (categoryTimeChart) {
    destroyExistingChart('categoryTimeChart');
    const categoryLabels = CATEGORY_TIME_DATA.map(item => item.category);
    const categoryCounts = CATEGORY_TIME_DATA.map(item => item.daily_count);
    
    new Chart(categoryTimeChart, {
      type: 'bar',
      data: {
        labels: categoryLabels,
        datasets: [{
          label: 'Tickets by Category',
          data: categoryCounts,
          backgroundColor: categoryLabels.map((_, i) => {
            const colors = ['#172d69', '#123692', '#dc3545'];
            return colors[i % colors.length];
          }),
          borderRadius: 8,
          barThickness: 30,
          hoverBackgroundColor: categoryLabels.map((_, i) => {
            const colors = ['#123692', '#172d69', '#b02a37'];
            return colors[i % colors.length];
          })
        }]
      },
      options: {
        ...animationOptions,
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const category = categoryLabels[index];
            fetchAndShowTickets(`/api/tickets/?category=${encodeURIComponent(category)}`, `${category} Tickets`);
          }
        }
      }
    });
  }

  const overviewChart = document.getElementById('overviewChart');
    if (typeof OVERVIEW_DATA !== 'undefined' && overviewChart) {
        const overviewLabels = OVERVIEW_DATA.map(item => item.label);
        const overviewCounts = OVERVIEW_DATA.map(item => item.count);

        destroyExistingChart('overviewChart');

        new Chart(overviewChart, {
            type: 'bar',
            data: {
                labels: overviewLabels,
                datasets: [{
                    label: 'Tickets',
                    data: overviewCounts,
                    backgroundColor: ['#123692', '#172d69', '#dc3545', '#007bff'],
                    borderRadius: 6,
                    barThickness: 40
                }]
            },
            options: {
                ...animationOptions,
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const PERIOD_MAP = {
                          "today": "today",
                          "this week": "week",
                          "this month": "month",
                          "this year": "year",
                          "day": "day",
                          "week": "week",
                          "month": "month",
                          "year": "year"
                        };

                        const label = overviewLabels[index].toLowerCase();
                        const period = PERIOD_MAP[label];

                        if (!period) {
                          console.warn("Unknown period label:", label);
                          return;
                        }

                        fetchAndShowTickets(
                          `/api/tickets/?period=${period}`,
                          `${overviewLabels[index]} Tickets`
                        );
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

  const customerChart = document.getElementById('customerChart');
  if (customerChart) {
    destroyExistingChart('customerChart');
    const customerLabels = CUSTOMER_DATA.map(c => c.customer);
    const customerCounts = CUSTOMER_DATA.map(c => c.count);
    
    new Chart(customerChart, {
      type: 'bar',
      data: {
        labels: customerLabels,
        datasets: [{
          label: 'Tickets',
          data: customerCounts,
          backgroundColor: customerLabels.map((_, i) => {
            const colors = ['#123692', '#dc3545', '#172d69'];
            return colors[i % colors.length];
          }),
          borderRadius: 8,
          barThickness: 30,
          hoverBackgroundColor: customerLabels.map((_, i) => {
            const colors = ['#172d69', '#b02a37', '#123692'];
            return colors[i % colors.length];
          })
        }]
      },
      options: {
        ...animationOptions,
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const customer = customerLabels[index];
            fetchAndShowTickets(`/api/tickets/?customer=${encodeURIComponent(customer)}`, `Tickets for ${customer}`);
          }
        }
      }
    });
  }

  console.log("ticketing_dashboard.js executed successfully. Chart.js available:", typeof Chart !== "undefined");

  function renderTicketsTable(tickets, page = 1, perPage = 10) {
    const modalBody = document.querySelector('.modal-tickets');
    modalBody.innerHTML = '';

    const start = (page - 1) * perPage;
    const end = start + perPage;
    const paginatedTickets = tickets.slice(start, end);

    let tableHTML = `
      <div class="table-responsive">
        <table class="tickets-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Created By</th>
              <th>Assigned To</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
    `;

    paginatedTickets.forEach(t => {
      const statusClass = {
        open: 'status-open',
        in_progress: 'status-in_progress',
        resolved: 'status-resolved',
        closed: 'status-closed'
      }[t.status] || 'status-open';

      const priorityClass = {
        low: 'priority-low',
        medium: 'priority-medium',
        high: 'priority-high',
        critical: 'priority-critical'
      }[t.priority] || 'priority-medium';

      tableHTML += `
        <tr class="ticket-row" data-id="${t.id}">
          <td>#${t.id}</td>
          <td title="${t.title || 'Untitled'}">${t.title?.length > 25 ? t.title.slice(0, 25) + '…' : t.title || 'Untitled'}</td>
          <td><span class="badge badge-status ${statusClass}">${t.status || 'Unknown'}</span></td>
          <td><span class="badge badge-priority ${priorityClass}">${t.priority || 'Unknown'}</span></td>
          <td title="${t.created_by || 'Unknown'}">${t.created_by?.length > 15 ? t.created_by.slice(0, 15) + '…' : t.created_by || 'Unknown'}</td>
          <td title="${t.assigned_to || '-'}">${t.assigned_to?.length > 15 ? t.assigned_to.slice(0, 15) + '…' : t.assigned_to || '-'}</td>
          <td>${t.created_at}</td>
        </tr>
      `;
    });

    tableHTML += `</tbody></table></div>`;

    // Pagination controls with only First, Previous, Next, Last
    const totalPages = Math.ceil(tickets.length / perPage);
    let paginationHTML = `<div class="pagination">`;

    if (page > 1) {
      paginationHTML += `<button class="page-btn first-btn" data-page="1">First</button>`;
      paginationHTML += `<button class="page-btn prev-btn" data-page="${page - 1}">Previous</button>`;
    }

    if (page < totalPages) {
      paginationHTML += `<button class="page-btn next-btn" data-page="${page + 1}">Next</button>`;
      paginationHTML += `<button class="page-btn last-btn" data-page="${totalPages}">Last</button>`;
    }

    paginationHTML += `</div>`;

    //modalBody.innerHTML = tableHTML + paginationHTML;
    modalBody.innerHTML = `
    <p>Total Tickets: ${tickets.length}</p>
      <div class="table-responsive">
        ${tableHTML}
        ${paginationHTML}
      </div>
    `;


    // Attach pagination events
    modalBody.querySelectorAll('.page-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        renderTicketsTable(tickets, parseInt(btn.dataset.page), perPage);
      });
    });

    // Attach row click events
    modalBody.querySelectorAll('.ticket-row').forEach(row => {
      row.addEventListener('click', () => {
        const ticketId = row.dataset.id;
        window.location.href = `/tickets/${ticketId}/`;
      });
    });
  }

});
