// ServerPulse - Performance Page Charts & Analytics
let pCpuChart = null;
let pRamChart = null;
let pNetChart = null;

let selectedServerId = null;
let currentWindow = 30;
let serverCache = [];

document.addEventListener('DOMContentLoaded', async () => {
  initPerfCharts();
  await populateServerDropdown();
  fetchPerformanceMetrics();

  setInterval(fetchPerformanceMetrics, 3500);
});

async function populateServerDropdown() {
  try {
    const res = await fetch('/api/servers');
    serverCache = await res.json();
    const select = document.getElementById('serverSelect');
    if (!select) return;

    select.innerHTML = serverCache.map(s => {
      const tag = s.is_local == 1 ? '[REAL HOST]' : '[SIMULATED]';
      return `<option value="${s.id}">${tag} ${s.name} (${s.ip_address})</option>`;
    }).join('');

    if (serverCache.length > 0) {
      selectedServerId = serverCache[0].id;
      select.value = selectedServerId;
    }
  } catch (err) {
    console.error('Error populating server dropdown:', err);
  }
}

function onServerChange() {
  const select = document.getElementById('serverSelect');
  selectedServerId = parseInt(select.value);
  fetchPerformanceMetrics();
}

function setTimeWindow(samples, btn) {
  currentWindow = samples;
  document.querySelectorAll('.tabs-group .tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  fetchPerformanceMetrics();
}

function initPerfCharts() {
  const commonOptions = {
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
  const cpuCtx = document.getElementById('perfCpuChart').getContext('2d');
  const cpuGrad = cpuCtx.createLinearGradient(0, 0, 0, 300);
  cpuGrad.addColorStop(0, 'rgba(6, 182, 212, 0.4)');
  cpuGrad.addColorStop(1, 'rgba(6, 182, 212, 0.0)');

  pCpuChart = new Chart(cpuCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'CPU (%)',
        data: [],
        borderColor: '#06b6d4',
        borderWidth: 2,
        backgroundColor: cpuGrad,
        fill: true,
        tension: 0.35,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: commonOptions
  });

  // RAM Chart
  const ramCtx = document.getElementById('perfRamChart').getContext('2d');
  const ramGrad = ramCtx.createLinearGradient(0, 0, 0, 300);
  ramGrad.addColorStop(0, 'rgba(139, 92, 246, 0.4)');
  ramGrad.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

  pRamChart = new Chart(ramCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'RAM (%)',
        data: [],
        borderColor: '#8b5cf6',
        borderWidth: 2,
        backgroundColor: ramGrad,
        fill: true,
        tension: 0.35,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: commonOptions
  });

  // Network Chart
  const netCtx = document.getElementById('perfNetChart').getContext('2d');
  const netOpts = JSON.parse(JSON.stringify(commonOptions));
  delete netOpts.scales.y.max;
  netOpts.scales.y.ticks.callback = (val) => `${val} KB/s`;
  netOpts.plugins.legend = {
    display: true,
    position: 'top',
    labels: { color: '#94a3b8', font: { size: 11 }, boxWidth: 12 }
  };

  pNetChart = new Chart(netCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Upload (Tx)',
          data: [],
          borderColor: '#f59e0b',
          borderWidth: 2,
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          tension: 0.35,
          pointRadius: 2
        },
        {
          label: 'Download (Rx)',
          data: [],
          borderColor: '#3b82f6',
          borderWidth: 2,
          backgroundColor: 'rgba(59, 130, 246, 0.08)',
          tension: 0.35,
          pointRadius: 2
        }
      ]
    },
    options: netOpts
  });
}

async function fetchPerformanceMetrics() {
  if (!selectedServerId) return;

  try {
    const res = await fetch(`/api/metrics/history?server_id=${selectedServerId}&limit=${currentWindow}`);
    if (!res.ok) throw new Error('Failed to fetch metric history');
    const data = await res.json();

    const server = data.server || {};
    document.getElementById('perfCoresBadge').textContent = `${server.cpu_cores || 4} CPU Cores`;
    document.getElementById('perfRamTotalBadge').textContent = `${server.total_ram_gb || 16} GB RAM`;
    document.getElementById('perfCpuSub').textContent = `${server.name} – CPU Load Time Series`;
    document.getElementById('perfRamSub').textContent = `${server.name} – Memory Consumption`;

    if (data.labels && data.labels.length > 0) {
      // Update Charts
      pCpuChart.data.labels = data.labels;
      pCpuChart.data.datasets[0].data = data.cpu;
      pCpuChart.update('none');

      pRamChart.data.labels = data.labels;
      pRamChart.data.datasets[0].data = data.ram;
      pRamChart.update('none');

      pNetChart.data.labels = data.labels;
      pNetChart.data.datasets[0].data = data.net_sent;
      pNetChart.data.datasets[1].data = data.net_recv;
      pNetChart.update('none');

      // Update KPI callout cards with latest values
      const lastCpu = data.cpu[data.cpu.length - 1];
      const lastRam = data.ram[data.ram.length - 1];
      const lastTx = data.net_sent[data.net_sent.length - 1];
      const lastRx = data.net_recv[data.net_recv.length - 1];

      document.getElementById('perfCurrentCpu').textContent = `${lastCpu}%`;
      document.getElementById('perfCurrentRam').textContent = `${lastRam}%`;
      document.getElementById('perfCurrentRx').textContent = `${lastRx} KB/s`;
      document.getElementById('perfCurrentTx').textContent = `${lastTx} KB/s`;

      // Update Disk Section
      if (data.disk) {
        const diskPct = data.disk.percent || 0;
        document.getElementById('perfCurrentDisk').textContent = `${diskPct}%`;
        document.getElementById('perfDiskBadge').textContent = `${diskPct}% Allocated`;
        document.getElementById('perfDiskUsedLabel').textContent = `Used: ${data.disk.used_gb} GB`;
        document.getElementById('perfDiskFreeLabel').textContent = `Free: ${data.disk.free_gb} GB`;

        const fill = document.getElementById('perfDiskProgress');
        fill.style.width = `${diskPct}%`;
        fill.className = 'progress-fill';
        if (diskPct >= 90) fill.classList.add('critical');
        else if (diskPct >= 80) fill.classList.add('warning');

        document.getElementById('perfDiskBoxUsed').textContent = `${data.disk.used_gb} GB`;
        document.getElementById('perfDiskBoxFree').textContent = `${data.disk.free_gb} GB`;
        document.getElementById('perfDiskBoxTotal').textContent = `${data.disk.total_gb} GB`;
      }
    }
  } catch (err) {
    console.error('Error fetching performance metrics:', err);
  }
}

async function triggerSelectedSpike() {
  if (!selectedServerId) return;
  try {
    const res = await fetch(`/api/servers/${selectedServerId}/spike`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cpu: 96.0, ram: 93.0, cycles: 7 })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Simulated load spike active! Watch the performance curves surge.', 'warning');
      fetchPerformanceMetrics();
    }
  } catch (err) {
    showToast('Failed to trigger spike.', 'danger');
  }
}
