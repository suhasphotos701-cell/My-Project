// ServerPulse - Main Dashboard JavaScript
let cpuChart = null;
let ramChart = null;
let netChart = null;
let localServerId = null;

document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  fetchDashboardData();
  fetchHistoricalMetrics();

  // Polling every 3.5 seconds
  setInterval(() => {
    fetchDashboardData();
    fetchHistoricalMetrics();
  }, 3500);
});

function initCharts() {
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8', font: { size: 10 } }
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: {
          color: '#94a3b8',
          font: { size: 10 },
          callback: (val) => `${val}%`
        }
      }
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#151e32',
        titleColor: '#fff',
        bodyColor: '#94a3b8',
        borderColor: '#232f48',
        borderWidth: 1,
        padding: 10
      }
    }
  };

  // CPU Chart
  const cpuCtx = document.getElementById('dashboardCpuChart').getContext('2d');
  const cpuGradient = cpuCtx.createLinearGradient(0, 0, 0, 240);
  cpuGradient.addColorStop(0, 'rgba(6, 182, 212, 0.35)');
  cpuGradient.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

  cpuChart = new Chart(cpuCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'CPU Usage',
        data: [],
        borderColor: '#06b6d4',
        borderWidth: 2,
        backgroundColor: cpuGradient,
        fill: true,
        tension: 0.35,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: chartOptions
  });

  // RAM Chart
  const ramCtx = document.getElementById('dashboardRamChart').getContext('2d');
  const ramGradient = ramCtx.createLinearGradient(0, 0, 0, 240);
  ramGradient.addColorStop(0, 'rgba(139, 92, 246, 0.35)');
  ramGradient.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

  ramChart = new Chart(ramCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'RAM Usage',
        data: [],
        borderColor: '#8b5cf6',
        borderWidth: 2,
        backgroundColor: ramGradient,
        fill: true,
        tension: 0.35,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: chartOptions
  });

  // Network Chart (KB/s)
  const netCtx = document.getElementById('dashboardNetChart').getContext('2d');
  const netOptions = JSON.parse(JSON.stringify(chartOptions));
  delete netOptions.scales.y.max; // auto-scale for KB/s
  netOptions.scales.y.ticks.callback = (val) => `${val} KB/s`;
  netOptions.plugins.legend = {
    display: true,
    position: 'top',
    labels: { color: '#94a3b8', font: { size: 11 }, boxWidth: 12 }
  };

  netChart = new Chart(netCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Upload (Tx)',
          data: [],
          borderColor: '#f59e0b',
          borderWidth: 2,
          backgroundColor: 'rgba(245, 158, 11, 0.05)',
          tension: 0.35,
          pointRadius: 1
        },
        {
          label: 'Download (Rx)',
          data: [],
          borderColor: '#3b82f6',
          borderWidth: 2,
          backgroundColor: 'rgba(59, 130, 246, 0.05)',
          tension: 0.35,
          pointRadius: 1
        }
      ]
    },
    options: netOptions
  });
}

// Fetch overview metrics & recent alerts
async function fetchDashboardData() {
  try {
    const res = await fetch('/api/dashboard');
    if (!res.ok) throw new Error('Network response not ok');
    const data = await res.json();

    // Populate KPI Cards
    document.getElementById('kpiTotalServers').textContent = data.total_servers;
    document.getElementById('kpiOnlineServers').textContent = data.online_servers;
    document.getElementById('kpiOfflineServers').textContent = data.offline_servers;
    document.getElementById('kpiAvgCpu').textContent = `${data.avg_cpu}%`;
    document.getElementById('kpiAvgRam').textContent = `${data.avg_ram}%`;
    
    const activeAlertsEl = document.getElementById('kpiActiveAlerts');
    activeAlertsEl.textContent = data.active_alerts;
    if (data.active_alerts > 0) {
      activeAlertsEl.style.color = 'var(--accent-red)';
    } else {
      activeAlertsEl.style.color = 'var(--accent-green)';
    }

    // Populate Server Status Overview Table
    renderServerTable(data.servers);

    // Populate Recent Alerts Table
    renderRecentAlerts(data.recent_alerts);

  } catch (err) {
    console.error('Error fetching dashboard summary:', err);
  }
}

// Fetch historical time series for charts
async function fetchHistoricalMetrics() {
  try {
    const url = localServerId ? `/api/metrics/history?server_id=${localServerId}&limit=25` : `/api/metrics/history?limit=25`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Historical metrics error');
    const data = await res.json();

    if (data.server && data.server.id) {
      localServerId = data.server.id;
      document.getElementById('cpuChartSubtitle').textContent = `${data.server.name} – CPU Load (%)`;
      document.getElementById('ramChartSubtitle').textContent = `${data.server.name} – Memory (${data.server.total_ram_gb} GB Total)`;
    }

    if (data.labels && data.labels.length > 0) {
      // Update CPU
      cpuChart.data.labels = data.labels;
      cpuChart.data.datasets[0].data = data.cpu;
      cpuChart.update('none');

      // Update RAM
      ramChart.data.labels = data.labels;
      ramChart.data.datasets[0].data = data.ram;
      ramChart.update('none');

      // Update Network
      netChart.data.labels = data.labels;
      netChart.data.datasets[0].data = data.net_sent;
      netChart.data.datasets[1].data = data.net_recv;
      netChart.update('none');

      // Update Network badge
      const lastRx = data.net_recv[data.net_recv.length - 1] || 0;
      const lastTx = data.net_sent[data.net_sent.length - 1] || 0;
      document.getElementById('netRateBadge').textContent = `↓${lastRx} KB/s  ↑${lastTx} KB/s`;

      // Update Disk info
      if (data.disk) {
        const diskPct = data.disk.percent || 0;
        document.getElementById('diskPercentBadge').textContent = `${diskPct}% Used`;
        document.getElementById('diskUsageLabel').textContent = `${data.disk.used_gb} GB / ${data.disk.total_gb} GB`;
        
        const fill = document.getElementById('diskProgressFill');
        fill.style.width = `${diskPct}%`;
        fill.className = 'progress-fill';
        if (diskPct >= 90) fill.classList.add('critical');
        else if (diskPct >= 80) fill.classList.add('warning');

        document.getElementById('diskUsedVal').textContent = `${data.disk.used_gb} GB`;
        document.getElementById('diskFreeVal').textContent = `${data.disk.free_gb} GB`;
        document.getElementById('diskTotalVal').textContent = `${data.disk.total_gb} GB`;
      }
    }
  } catch (err) {
    console.error('Error fetching historical metrics:', err);
  }
}

function renderServerTable(servers) {
  const tbody = document.getElementById('serverOverviewBody');
  if (!tbody) return;

  if (!servers || servers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty-state">No servers found.</td></tr>`;
    return;
  }

  tbody.innerHTML = servers.map(s => {
    const isOnline = s.status === 'online';
    const metric = s.latest_metric;
    const cpuPct = isOnline && metric ? metric.cpu_percent : 0;
    const ramPct = isOnline && metric ? metric.ram_percent : 0;
    const diskPct = isOnline && metric ? metric.disk_percent : 0;

    const cpuColor = cpuPct >= 90 ? 'var(--accent-red)' : (cpuPct >= 80 ? 'var(--accent-yellow)' : 'var(--accent-cyan)');
    const ramColor = ramPct >= 95 ? 'var(--accent-red)' : (ramPct >= 85 ? 'var(--accent-yellow)' : 'var(--accent-purple)');
    const diskColor = diskPct >= 90 ? 'var(--accent-red)' : (diskPct >= 80 ? 'var(--accent-yellow)' : 'var(--accent-green)');

    const typeBadge = s.is_local == 1 
      ? `<span class="badge badge-real">LOCAL HOST</span>`
      : `<span class="badge badge-simulated">SIMULATED</span>`;

    const statusBadge = isOnline
      ? `<span class="badge badge-online">ONLINE</span>`
      : `<span class="badge badge-offline">OFFLINE</span>`;

    return `
      <tr>
        <td><strong>${s.name}</strong></td>
        <td>${typeBadge}</td>
        <td><code>${s.ip_address}</code></td>
        <td style="color: var(--text-secondary);">${s.os_info}</td>
        <td>
          <div class="mini-bar-container">
            <div class="mini-bar">
              <div class="mini-bar-fill" style="width: ${cpuPct}%; background-color: ${cpuColor};"></div>
            </div>
            <span class="mini-bar-text" style="color: ${cpuColor};">${isOnline ? cpuPct + '%' : '--'}</span>
          </div>
        </td>
        <td>
          <div class="mini-bar-container">
            <div class="mini-bar">
              <div class="mini-bar-fill" style="width: ${ramPct}%; background-color: ${ramColor};"></div>
            </div>
            <span class="mini-bar-text" style="color: ${ramColor};">${isOnline ? ramPct + '%' : '--'}</span>
          </div>
        </td>
        <td>
          <div class="mini-bar-container">
            <div class="mini-bar">
              <div class="mini-bar-fill" style="width: ${diskPct}%; background-color: ${diskColor};"></div>
            </div>
            <span class="mini-bar-text" style="color: ${diskColor};">${isOnline ? diskPct + '%' : '--'}</span>
          </div>
        </td>
        <td>${statusBadge}</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${s.last_heartbeat || '--'}</td>
      </tr>
    `;
  }).join('');
}

function renderRecentAlerts(alerts) {
  const tbody = document.getElementById('recentAlertsBody');
  if (!tbody) return;

  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state" style="color: var(--accent-green);">No active alerts. All monitored servers are healthy!</td></tr>`;
    return;
  }

  tbody.innerHTML = alerts.map(a => {
    const sevBadge = a.severity === 'critical'
      ? `<span class="badge badge-critical">CRITICAL</span>`
      : `<span class="badge badge-warning">WARNING</span>`;

    const statusBadge = `<span class="badge badge-${a.status}">${a.status.toUpperCase()}</span>`;

    return `
      <tr>
        <td>${sevBadge}</td>
        <td><strong>${a.server_name}</strong></td>
        <td><span class="badge badge-info">${a.alert_type}</span></td>
        <td>${a.description}</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${a.created_at}</td>
        <td>${statusBadge}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            ${a.status === 'active' ? `<button class="btn btn-warning btn-sm" onclick="acknowledgeAlert(${a.id})">Ack</button>` : ''}
            <button class="btn btn-success btn-sm" onclick="resolveAlert(${a.id})">Resolve</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// Alert action handlers
async function acknowledgeAlert(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('Alert acknowledged by administrator.', 'warning');
      fetchDashboardData();
    }
  } catch (err) {
    showToast('Failed to acknowledge alert.', 'danger');
  }
}

async function resolveAlert(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/resolve`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('Alert resolved successfully.', 'success');
      fetchDashboardData();
    }
  } catch (err) {
    showToast('Failed to resolve alert.', 'danger');
  }
}

// University Demo Helper: Trigger spike on simulated node or local server
async function triggerDemoSpike() {
  try {
    // Pick the first simulated server or local server
    const res = await fetch('/api/servers');
    const servers = await res.json();
    const target = servers.find(s => s.is_local === 0) || servers[0];

    if (!target) {
      showToast('No servers available for spike simulation.', 'warning');
      return;
    }

    const spikeRes = await fetch(`/api/servers/${target.id}/spike`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cpu: 94.5, ram: 91.0, cycles: 7 })
    });
    const spikeData = await spikeRes.json();
    if (spikeData.success) {
      showToast(`High CPU & RAM load spike simulated on ${target.name}! Watch for alerts.`, 'warning');
      fetchDashboardData();
      fetchHistoricalMetrics();
    }
  } catch (err) {
    showToast('Failed to trigger simulation spike.', 'danger');
  }
}
