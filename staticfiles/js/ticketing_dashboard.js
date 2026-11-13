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
        /*document.getElementById("dailyCount").textContent = timeData.day;
        document.getElementById("weeklyCount").textContent = timeData.week;
        document.getElementById("monthlyCount").textContent = timeData.month;
        document.getElementById("yearlyCount").textContent = timeData.year;*/

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

  // =====================================================================
  //  CHART APPEARANCE
  //  Only how charts look and move is defined here. Data, click handlers
  //  and endpoints are exactly as before.
  // =====================================================================
  const HAS_CHART = typeof Chart !== 'undefined';
  const HAS_LABELS = typeof ChartDataLabels !== 'undefined';
  const REDUCED_MOTION = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.body).getPropertyValue(name).trim();
    return v || fallback;
  }

  // Brand + system colours (priority/status values match tickets.css exactly)
  const BRAND = {
    navy: '#123692', deep: '#172d69', sky: '#4f7be8',
    red: '#dc3545', redDeep: '#b02a37',
  };
  const PRIORITY_COLORS = { low: '#17b845', medium: '#007bff', high: '#dc9c35', critical: '#e74c3c' };
  const STATUS_COLORS = { open: '#007bff', in_progress: '#c0392b', resolved: '#28a745', closed: '#6c757d' };

  const THEME = {
    text: cssVar('--dash-text', '#1b2540'),
    muted: cssVar('--dash-muted', '#6b7489'),
    grid: cssVar('--dash-grid', 'rgba(18, 54, 146, 0.07)'),
    surface: cssVar('--card-background', '#ffffff'),
    font: getComputedStyle(document.body).fontFamily || "'Segoe UI', Roboto, sans-serif",
  };

  if (HAS_CHART) {
    Chart.defaults.font.family = THEME.font;
    Chart.defaults.color = THEME.muted;
  }

  // ── Fills ─────────────────────────────────────────────────────────────
  function withAlpha(hex, a) {
    const h = hex.replace('#', '');
    const n = parseInt(h.length === 3 ? h.split('').map(c => c + c).join('') : h, 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
  }

  // Bar fill: brand gradient, the busiest bar in red so it stands out
  function barFill(values, horizontal = false) {
    const max = Math.max(...values.map(v => +v || 0));
    return (ctx) => {
      const { chart, dataIndex } = ctx;
      const area = chart.chartArea;
      const isTop = (+values[dataIndex] || 0) === max && max > 0;
      const [from, to] = isTop ? [BRAND.redDeep, '#f0616f'] : [BRAND.deep, BRAND.sky];
      if (!area) return isTop ? BRAND.red : BRAND.navy;
      const g = horizontal
        ? chart.ctx.createLinearGradient(area.left, 0, area.right, 0)
        : chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
      g.addColorStop(0, from);
      g.addColorStop(1, to);
      return g;
    };
  }

  // Area fill under line charts
  function areaFill(hex) {
    return (ctx) => {
      const area = ctx.chart.chartArea;
      if (!area) return withAlpha(hex, 0.12);
      const g = ctx.chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
      g.addColorStop(0, withAlpha(hex, 0.28));
      g.addColorStop(1, withAlpha(hex, 0.01));
      return g;
    };
  }

  // ── Motion ────────────────────────────────────────────────────────────
  const barMotion = REDUCED_MOTION ? { animation: false } : {
    animation: {
      duration: 900,
      easing: 'easeOutQuart',
      delay: (ctx) => (ctx.type === 'data' && ctx.mode === 'default') ? ctx.dataIndex * 70 : 0,
    },
  };

  // The line draws itself from left to right
  function lineMotion(pointCount) {
    if (REDUCED_MOTION) return { animation: false };
    const per = 1200 / Math.max(pointCount, 1);
    const prevY = (ctx) => {
      if (ctx.index === 0) return ctx.chart.scales.y.getPixelForValue(0);
      return ctx.chart.getDatasetMeta(ctx.datasetIndex).data[ctx.index - 1].getProps(['y'], true).y;
    };
    return {
      animations: {
        x: {
          type: 'number', easing: 'linear', duration: per, from: NaN,
          delay(ctx) { if (ctx.type !== 'data' || ctx.xStarted) return 0; ctx.xStarted = true; return ctx.index * per; },
        },
        y: {
          type: 'number', easing: 'linear', duration: per, from: prevY,
          delay(ctx) { if (ctx.type !== 'data' || ctx.yStarted) return 0; ctx.yStarted = true; return ctx.index * per; },
        },
      },
    };
  }

  const doughnutMotion = REDUCED_MOTION ? { animation: false } : {
    animation: { animateRotate: true, animateScale: true, duration: 1100, easing: 'easeOutQuart' },
  };

  // ── Shared pieces ─────────────────────────────────────────────────────
  const tooltipStyle = {
    backgroundColor: '#0f1d4a',
    titleColor: '#ffffff',
    bodyColor: 'rgba(255,255,255,0.88)',
    titleFont: { size: 13, weight: '600', family: THEME.font },
    bodyFont: { size: 12, family: THEME.font },
    padding: 12,
    cornerRadius: 10,
    caretSize: 6,
    boxPadding: 5,
    displayColors: true,
    usePointStyle: true,
    borderColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
  };

  function integerTicks(value) { return Number.isInteger(value) ? value.toLocaleString() : null; }

  function cartesianScales({ horizontal = false } = {}) {
    const valueAxis = {
      beginAtZero: true,
      grace: '8%',
      border: { display: false },
      grid: { color: THEME.grid, drawTicks: false },
      ticks: { color: THEME.muted, padding: 8, font: { size: 11 }, callback: integerTicks },
    };
    const categoryAxis = {
      border: { display: false },
      grid: { display: false },
      ticks: {
        color: THEME.muted, padding: 6, font: { size: 11 },
        autoSkip: !horizontal, autoSkipPadding: 10, maxRotation: 0,
        // Long labels wrap onto two lines instead of slanting
        callback(value) {
          const label = this.getLabelForValue(value) || '';
          if (horizontal) return label.length > 34 ? label.slice(0, 33) + '…' : label;
          if (label.length <= 14) return label;
          const lines = [];
          label.split(' ').forEach(w => {
            const cur = lines.length ? lines[lines.length - 1] : '';
            if (!lines.length) lines.push(w);
            else if ((cur + ' ' + w).length > 16 && lines.length < 2) lines.push(w);
            else lines[lines.length - 1] = cur + ' ' + w;
          });
          return lines.map(l => l.length > 18 ? l.slice(0, 17) + '…' : l);
        },
      },
    };
    return horizontal ? { x: valueAxis, y: categoryAxis } : { x: categoryAxis, y: valueAxis };
  }

  const barValueLabels = (horizontal = false) => ({
    anchor: 'end',
    align: 'end',
    offset: 2,
    clamp: true,
    color: THEME.text,
    font: { size: 11, weight: '600' },
    formatter: (v) => (+v > 0 ? (+v).toLocaleString() : ''),
  });

  const sliceLabels = {
    color: '#ffffff',
    font: { size: 11, weight: '700' },
    formatter: (value, ctx) => {
      const total = ctx.dataset.data.reduce((a, b) => a + (+b || 0), 0);
      const pct = total ? (value / total) * 100 : 0;
      return pct >= 6 ? `${Math.round(pct)}%` : '';
    },
  };

  // Total in the middle of a doughnut
  const centerTotal = {
    id: 'centerTotal',
    afterDraw(chart) {
      const meta = chart.getDatasetMeta(0);
      if (!meta || !meta.data || !meta.data.length) return;
      const arc = meta.data[0];
      const r = arc.innerRadius;
      if (!r) return;
      const total = chart.data.datasets[0].data.reduce((a, b) => a + (+b || 0), 0);
      const c = chart.ctx;
      c.save();
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillStyle = THEME.text;
      c.font = `700 ${Math.round(r * 0.42)}px ${THEME.font}`;
      c.fillText(total.toLocaleString(), arc.x, arc.y - r * 0.1);
      c.fillStyle = THEME.muted;
      c.font = `500 ${Math.max(11, Math.round(r * 0.15))}px ${THEME.font}`;
      c.fillText('tickets', arc.x, arc.y + r * 0.3);
      c.restore();
    },
  };

  function basePlugins(extra = {}) {
    return {
      legend: { display: false },
      tooltip: tooltipStyle,
      ...extra,
    };
  }

  function labelPlugins() { return HAS_LABELS ? [ChartDataLabels] : []; }

  // Build a chart only when it scrolls into view, so its animation is seen
  function whenVisible(canvas, build) {
    const target = canvas.closest('.chart-card') || canvas;
    if (!('IntersectionObserver' in window) || REDUCED_MOTION) { build(); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { io.disconnect(); build(); }
      });
    }, { threshold: 0.2 });
    io.observe(target);
  }

  // ── KPI numbers count up ──────────────────────────────────────────────
  document.querySelectorAll('.kpi-card .details p').forEach(el => {
    const target = parseInt((el.textContent || '').replace(/[^0-9]/g, ''), 10);
    if (isNaN(target)) return;
    if (REDUCED_MOTION || target === 0) { el.textContent = target.toLocaleString(); return; }
    const start = performance.now(), duration = 1100;
    el.textContent = '0';
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased).toLocaleString();
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  // =====================================================================
  //  CHARTS
  // =====================================================================

  const ticketReportChart = document.getElementById('ticketReportChart');
  if (ticketReportChart && HAS_CHART) {
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
          backgroundColor: STATUS_DATA.map(item => STATUS_COLORS[item.status.toLowerCase().replace(' ', '_')] || BRAND.navy),
          borderRadius: 8,
          borderSkipped: false,
          minBarLength: 3,
          maxBarThickness: 46
        }]
      },
      plugins: labelPlugins(),
      options: {
        responsive: true, maintainAspectRatio: false, ...barMotion,
        layout: { padding: { top: 18 } },
        plugins: basePlugins({ datalabels: barValueLabels() }),
        scales: cartesianScales()
      }
    });
  }

  const monthlyTrendChart = document.getElementById('monthlyTrendChart');
  if (monthlyTrendChart && HAS_CHART) {
    whenVisible(monthlyTrendChart, () => {
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
            borderColor: BRAND.navy,
            backgroundColor: areaFill(BRAND.navy),
            borderWidth: 2.5,
            tension: 0.4,
            fill: true,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: BRAND.navy,
            pointBorderWidth: 2,
            pointRadius: 3.5,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: BRAND.navy,
            pointHoverBorderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, ...lineMotion(monthlyCounts.length),
          interaction: { mode: 'index', intersect: false },
          plugins: basePlugins(),
          scales: cartesianScales()
        }
      });
    });
  }

  const terminalChart = document.getElementById('terminalChart');
  if (terminalChart && HAS_CHART) {
    // Horizontal bars: terminal names are long and read better this way
    const box = terminalChart.closest('.chart-box');
    if (box) box.style.height = Math.max(300, TERMINAL_DATA.length * 40 + 40) + 'px';
    whenVisible(terminalChart, () => {
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
            backgroundColor: barFill(terminalCounts, true),
            borderRadius: 6,
            borderSkipped: false,
            minBarLength: 3,
            barPercentage: 0.72,
            categoryPercentage: 0.9,
            maxBarThickness: 26
          }]
        },
        plugins: labelPlugins(),
        options: {
          indexAxis: 'y',
          responsive: true, maintainAspectRatio: false, ...barMotion,
          layout: { padding: { right: 28 } },
          interaction: { mode: 'nearest', axis: 'y', intersect: true },
          plugins: basePlugins({ datalabels: barValueLabels(true) }),
          scales: cartesianScales({ horizontal: true }),
          onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
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
    });
  }

  // === Region-wise Ticket Volume ===
  const regionChart = document.getElementById('regionChart');
  if (regionChart && HAS_CHART) {
    whenVisible(regionChart, () => {
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
            backgroundColor: barFill(regionCounts),
            borderRadius: 8,
            borderSkipped: false,
            minBarLength: 3,
            maxBarThickness: 44
          }]
        },
        plugins: labelPlugins(),
        options: {
          responsive: true, maintainAspectRatio: false, ...barMotion,
          layout: { padding: { top: 18 } },
          interaction: { mode: 'index', intersect: false },
          plugins: basePlugins({ datalabels: barValueLabels() }),
          scales: cartesianScales(),
          onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
          onClick: (event, elements) => {
            if (elements.length > 0) {
              const index = elements[0].index;
              const region = regionLabels[index];
              fetchAndShowTickets(`/api/tickets/?region=${encodeURIComponent(region)}`, `Tickets in ${region}`);
            }
          }
        }
      });
    });
  }

  const priorityChart = document.getElementById('priorityChart');
  if (priorityChart && HAS_CHART) {
    whenVisible(priorityChart, () => {
      destroyExistingChart('priorityChart');
      const priorityData = PRIORITY_DATA.map(item => ({
        priority: item.priority,
        count: item.count
      }));
      const priorityLabels = priorityData.map(item => item.priority.charAt(0).toUpperCase() + item.priority.slice(1));
      const priorityCounts = priorityData.map(item => item.count);

      const priorityChartInstance = new Chart(priorityChart, {
        type: 'doughnut',
        data: {
          labels: priorityLabels,
          datasets: [{
            data: priorityCounts,
            backgroundColor: priorityData.map(item => PRIORITY_COLORS[item.priority.toLowerCase()] || '#6c757d'),
            borderColor: THEME.surface,
            borderWidth: 3,
            hoverOffset: 10,
            spacing: 2,
            borderRadius: 6
          }]
        },
        plugins: [centerTotal, ...labelPlugins()],
        options: {
          responsive: true, maintainAspectRatio: false, ...doughnutMotion,
          cutout: '64%',
          layout: { padding: 10 },
          onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
          onClick: (event, elements) => {
            if (elements.length > 0) {
              const index = elements[0].index;
              const priority = priorityData[index].priority;
              const priorityLabel = priorityLabels[index];
              fetchAndShowTickets(`/api/tickets/?priority=${priority}`, `${priorityLabel} Priority Tickets`)
            }
          },
          plugins: {
            legend: {
              display: true, position: 'bottom',
              labels: { usePointStyle: true, pointStyle: 'circle', boxWidth: 8, boxHeight: 8, padding: 16, color: THEME.text, font: { size: 12, weight: '500' } }
            },
            datalabels: sliceLabels,
            tooltip: {
              ...tooltipStyle,
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
    });
  }

  const statusChart = document.getElementById('statusChart');
  if (statusChart && HAS_CHART) {
    whenVisible(statusChart, () => {
      destroyExistingChart('statusChart');
      const statusData = STATUS_DATA.map(item => ({
        status: item.status,
        count: item.count
      }));
      const statusLabels = statusData.map(item => item.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()));
      const statusCounts = statusData.map(item => item.count);

      const statusChartInstance = new Chart(statusChart, {
        type: 'doughnut',
        data: {
          labels: statusLabels,
          datasets: [{
            data: statusCounts,
            backgroundColor: statusData.map(item => STATUS_COLORS[item.status.toLowerCase().replace(' ', '_')] || '#cccccc'),
            borderColor: THEME.surface,
            borderWidth: 3,
            hoverOffset: 10,
            spacing: 2,
            borderRadius: 6
          }]
        },
        plugins: [centerTotal, ...labelPlugins()],
        options: {
          responsive: true, maintainAspectRatio: false, ...doughnutMotion,
          cutout: '64%',
          layout: { padding: 10 },
          onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
          onClick: (event, elements) => {
            if (elements.length > 0) {
              const index = elements[0].index;
              const status = statusData[index].status;
              const statusLabel = statusLabels[index];
              fetchAndShowTickets(`/api/tickets/?status=${status}`, `${statusLabel} Tickets`);
            }
          },
          plugins: {
            legend: {
              display: true, position: 'bottom',
              labels: { usePointStyle: true, pointStyle: 'circle', boxWidth: 8, boxHeight: 8, padding: 16, color: THEME.text, font: { size: 12, weight: '500' } }
            },
            datalabels: sliceLabels,
            tooltip: {
              ...tooltipStyle,
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
    });
  }

  const timeTrendChart = document.getElementById('timeTrendChart');
  if (timeTrendChart && HAS_CHART) {
    whenVisible(timeTrendChart, () => {
      destroyExistingChart('timeTrendChart');
      new Chart(timeTrendChart, {
        type: 'line',
        data: {
          labels: ['Day', 'Week', 'Month', 'Year'],
          datasets: [{
            label: 'Ticket Volume',
            data: [TIME_DATA.day, TIME_DATA.week, TIME_DATA.month, TIME_DATA.year],
            borderColor: BRAND.red,
            backgroundColor: areaFill(BRAND.red),
            borderWidth: 2.5,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: BRAND.red,
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: BRAND.red,
            pointHoverBorderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, ...lineMotion(4),
          interaction: { mode: 'index', intersect: false },
          plugins: basePlugins(),
          scales: cartesianScales()
        }
      });
    });
  }

  const categoryChart = document.getElementById('categoryChart');
  if (categoryChart && HAS_CHART) {
    destroyExistingChart('categoryChart');
    const catCounts = CATEGORY_DATA.map(c => c.count);
    new Chart(categoryChart, {
      type: 'bar',
      data: {
        labels: CATEGORY_DATA.map(c => c.category),
        datasets: [{
          label: 'Tickets',
          data: catCounts,
          backgroundColor: barFill(catCounts),
          borderRadius: 8,
          borderSkipped: false,
          minBarLength: 3,
          maxBarThickness: 40
        }]
      },
      plugins: labelPlugins(),
      options: {
        responsive: true, maintainAspectRatio: false, ...barMotion,
        layout: { padding: { top: 18 } },
        plugins: basePlugins({ datalabels: barValueLabels() }),
        scales: cartesianScales()
      }
    });
  }

  const categoryTimeChart = document.getElementById('categoryTimeChart');
  if (categoryTimeChart && HAS_CHART) {
    whenVisible(categoryTimeChart, () => {
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
            backgroundColor: barFill(categoryCounts),
            borderRadius: 8,
            borderSkipped: false,
            minBarLength: 3,
            maxBarThickness: 52
          }]
        },
        plugins: labelPlugins(),
        options: {
          responsive: true, maintainAspectRatio: false, ...barMotion,
          layout: { padding: { top: 18 } },
          interaction: { mode: 'index', intersect: false },
          plugins: basePlugins({ datalabels: barValueLabels() }),
          scales: cartesianScales(),
          onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
          onClick: (event, elements) => {
            if (elements.length > 0) {
              const index = elements[0].index;
              const category = categoryLabels[index];
              fetchAndShowTickets(`/api/tickets/?category=${encodeURIComponent(category)}`, `${category} Tickets`);
            }
          }
        }
      });
    });
  }

  const overviewChart = document.getElementById('overviewChart');
  if (typeof OVERVIEW_DATA !== 'undefined' && overviewChart && HAS_CHART) {
    whenVisible(overviewChart, () => {
      const overviewLabels = OVERVIEW_DATA.map(item => item.label);
      const overviewCounts = OVERVIEW_DATA.map(item => item.count);

      destroyExistingChart('overviewChart');

      // Today → this year, from light to deep navy
      const shades = ['#7fa1f0', BRAND.sky, BRAND.navy, BRAND.deep];
      new Chart(overviewChart, {
        type: 'bar',
        data: {
          labels: overviewLabels,
          datasets: [{
            label: 'Tickets',
            data: overviewCounts,
            backgroundColor: overviewLabels.map((_, i) => shades[i % shades.length]),
            borderRadius: 8,
            borderSkipped: false,
            minBarLength: 3,
            maxBarThickness: 64
          }]
        },
        plugins: labelPlugins(),
        options: {
          responsive: true, maintainAspectRatio: false, ...barMotion,
          layout: { padding: { top: 18 } },
          interaction: { mode: 'index', intersect: false },
          plugins: basePlugins({ datalabels: barValueLabels() }),
          scales: cartesianScales(),
          onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
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
          }
        }
      });
    });
  }

  const customerChart = document.getElementById('customerChart');
  if (customerChart && HAS_CHART) {
    whenVisible(customerChart, () => {
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
            backgroundColor: barFill(customerCounts),
            borderRadius: 8,
            borderSkipped: false,
            minBarLength: 3,
            maxBarThickness: 52
          }]
        },
        plugins: labelPlugins(),
        options: {
          responsive: true, maintainAspectRatio: false, ...barMotion,
          layout: { padding: { top: 18 } },
          interaction: { mode: 'index', intersect: false },
          plugins: basePlugins({ datalabels: barValueLabels() }),
          scales: cartesianScales(),
          onHover: (event, elements) => { event.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
          onClick: (event, elements) => {
            if (elements.length > 0) {
              const index = elements[0].index;
              const customer = customerLabels[index];
              fetchAndShowTickets(`/api/tickets/?customer=${encodeURIComponent(customer)}`, `Tickets for ${customer}`);
            }
          }
        }
      });
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
