// ServerPulse - Server Management JavaScript
let currentServers = [];
let activeFilter = 'all';
let searchQuery = '';

document.addEventListener('DOMContentLoaded', () => {
  fetchServers();
  setInterval(fetchServers, 3500);

  const searchInput = document.getElementById('serverSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderServers();
    });
  }
});

async function fetchServers() {
  try {
    const res = await fetch('/api/servers');
    if (!res.ok) throw new Error('Failed to fetch servers');
    currentServers = await res.json();
    renderServers();
  } catch (err) {
    console.error('Error fetching servers:', err);
  }
}

function filterServers(filter, btn) {
  activeFilter = filter;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderServers();
}

function renderServers() {
  const tbody = document.getElementById('serversTableBody');
  if (!tbody) return;

  let filtered = currentServers.filter(s => {
    // Search query filter
    const matchesSearch = !searchQuery || 
      s.name.toLowerCase().includes(searchQuery) ||
      s.ip_address.toLowerCase().includes(searchQuery) ||
      (s.hostname && s.hostname.toLowerCase().includes(searchQuery)) ||
      (s.os_info && s.os_info.toLowerCase().includes(searchQuery));

    if (!matchesSearch) return false;

    // Tab filter
    if (activeFilter === 'online') return s.status === 'online';
    if (activeFilter === 'offline') return s.status === 'offline';
    if (activeFilter === 'real') return s.is_local == 1;
    if (activeFilter === 'simulated') return s.is_local == 0;
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-state">No matching servers found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(s => {
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

    const toggleText = isOnline ? 'Set Offline' : 'Set Online';
    const toggleClass = isOnline ? 'btn-danger' : 'btn-success';

    return `
      <tr>
        <td>
          <div style="display: flex; flex-direction: column;">
            <strong>${s.name}</strong>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${s.simulated_profile || 'standard'} profile</span>
          </div>
        </td>
        <td>${typeBadge}</td>
        <td>
          <div style="display: flex; flex-direction: column;">
            <code>${s.ip_address}</code>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${s.hostname || ''}</span>
          </div>
        </td>
        <td style="color: var(--text-secondary); font-size: 0.82rem;">${s.os_info}</td>
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
        <td style="text-align: right;">
          <div style="display: flex; gap: 5px; justify-content: flex-end; flex-wrap: wrap;">
            <button class="btn btn-secondary btn-sm" onclick="showServerDetails(${s.id})" title="Hardware Specs">
              Details
            </button>
            <button class="btn ${toggleClass} btn-sm" onclick="toggleServerStatus(${s.id})" title="Toggle connection status">
              ${toggleText}
            </button>
            ${s.is_local == 0 ? `
              <button class="btn btn-warning btn-sm" onclick="triggerServerSpike(${s.id})" title="Simulate high resource spike">
                Spike
              </button>
              <button class="btn btn-danger btn-sm" onclick="deleteServer(${s.id}, '${s.name}')" title="Remove server">
                &times;
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// Modal actions
function openAddServerModal() {
  document.getElementById('addServerModal').classList.add('open');
}

function closeAddServerModal() {
  document.getElementById('addServerModal').classList.remove('open');
  document.getElementById('addServerForm').reset();
}

async function handleAddServer(e) {
  e.preventDefault();
  const name = document.getElementById('addServerName').value.trim();
  const ip = document.getElementById('addServerIp').value.trim();
  const host = document.getElementById('addServerHost').value.trim();
  const os_info = document.getElementById('addServerOs').value.trim();
  const profile = document.getElementById('addServerProfile').value;
  const cores = parseInt(document.getElementById('addServerCores').value);
  const ram = parseFloat(document.getElementById('addServerRam').value);
  const disk = parseFloat(document.getElementById('addServerDisk').value);

  try {
    const res = await fetch('/api/servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        ip_address: ip,
        hostname: host,
        os_info,
        simulated_profile: profile,
        cpu_cores: cores,
        total_ram_gb: ram,
        total_disk_gb: disk
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      closeAddServerModal();
      fetchServers();
    } else {
      showToast(data.error || 'Failed to add server', 'danger');
    }
  } catch (err) {
    showToast('Network error while adding server.', 'danger');
  }
}

async function toggleServerStatus(serverId) {
  try {
    const res = await fetch(`/api/servers/${serverId}/toggle-status`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, data.new_status === 'offline' ? 'warning' : 'success');
      fetchServers();
    }
  } catch (err) {
    showToast('Failed to toggle server status.', 'danger');
  }
}

async function triggerServerSpike(serverId) {
  try {
    const res = await fetch(`/api/servers/${serverId}/spike`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cpu: 95.0, ram: 92.0, cycles: 7 })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Simulated spike triggered! Watch CPU/RAM spike and generate alerts.', 'warning');
      fetchServers();
    }
  } catch (err) {
    showToast('Failed to trigger spike.', 'danger');
  }
}

async function deleteServer(serverId, serverName) {
  if (!confirm(`Are you sure you want to remove server '${serverName}' from ServerPulse?`)) {
    return;
  }
  try {
    const res = await fetch(`/api/servers/${serverId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'info');
      fetchServers();
    } else {
      showToast(data.error || 'Failed to delete server.', 'danger');
    }
  } catch (err) {
    showToast('Network error while deleting server.', 'danger');
  }
}

function showServerDetails(serverId) {
  const s = currentServers.find(item => item.id === serverId);
  if (!s) return;

  const modal = document.getElementById('serverDetailsModal');
  const title = document.getElementById('detailsServerTitle');
  const content = document.getElementById('detailsModalContent');

  title.textContent = `${s.name} – Hardware & Telemetry Specs`;

  const m = s.latest_metric || {};
  const uptime = m.uptime_seconds 
    ? `${Math.floor(m.uptime_seconds / 86400)}d ${Math.floor((m.uptime_seconds % 86400) / 3600)}h ${Math.floor((m.uptime_seconds % 3600) / 60)}m`
    : 'Active';

  content.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 20px;">
      <div class="stat-box">
        <div class="title">System Type</div>
        <div class="val" style="font-size: 0.95rem; color: var(--accent-cyan);">${s.is_local == 1 ? 'Host Machine (Psutil)' : 'Simulated Node'}</div>
      </div>
      <div class="stat-box">
        <div class="title">Connection Status</div>
        <div class="val" style="font-size: 0.95rem; color: ${s.status === 'online' ? 'var(--accent-green)' : 'var(--accent-red)'};">${s.status.toUpperCase()}</div>
      </div>
      <div class="stat-box">
        <div class="title">IP Address</div>
        <div class="val" style="font-size: 0.95rem;">${s.ip_address}</div>
      </div>
      <div class="stat-box">
        <div class="title">Hostname</div>
        <div class="val" style="font-size: 0.95rem;">${s.hostname || 'N/A'}</div>
      </div>
      <div class="stat-box">
        <div class="title">CPU Processor</div>
        <div class="val" style="font-size: 0.95rem;">${s.cpu_cores || 4} Cores</div>
      </div>
      <div class="stat-box">
        <div class="title">Total RAM</div>
        <div class="val" style="font-size: 0.95rem;">${s.total_ram_gb} GB</div>
      </div>
      <div class="stat-box">
        <div class="title">Disk Capacity</div>
        <div class="val" style="font-size: 0.95rem;">${s.total_disk_gb} GB</div>
      </div>
      <div class="stat-box">
        <div class="title">Total Uptime</div>
        <div class="val" style="font-size: 0.95rem; color: var(--accent-green);">${uptime}</div>
      </div>
    </div>
    <div style="background-color: var(--bg-input); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); font-size: 0.85rem; color: var(--text-secondary);">
      <div><strong>OS Kernel / Build:</strong> ${s.os_info}</div>
      <div style="margin-top: 4px;"><strong>Workload Profile:</strong> ${s.simulated_profile || 'Default compute node'}</div>
      <div style="margin-top: 4px;"><strong>Last Telemetry Heartbeat:</strong> ${s.last_heartbeat || 'Just now'}</div>
    </div>
  `;

  modal.classList.add('open');
}

function closeServerDetailsModal() {
  document.getElementById('serverDetailsModal').classList.remove('open');
}
