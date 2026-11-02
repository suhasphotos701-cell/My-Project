// ServerPulse - Alert Management JavaScript
let currentAlerts = [];
let activeStatusFilter = 'all';
let activeSeverityFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  fetchAlerts();
  setInterval(fetchAlerts, 3500);
});

async function fetchAlerts() {
  try {
    let url = `/api/alerts?status=${activeStatusFilter}`;
    if (activeSeverityFilter !== 'all') {
      url += `&severity=${activeSeverityFilter}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    currentAlerts = await res.json();
    
    // Also fetch all alerts count for KPI cards
    const allRes = await fetch('/api/alerts?status=all');
    if (allRes.ok) {
      const allList = await allRes.json();
      updateAlertKpis(allList);
    }

    renderAlertsTable();
  } catch (err) {
    console.error('Error fetching alerts:', err);
  }
}

function updateAlertKpis(allList) {
  const activeCount = allList.filter(a => a.status === 'active').length;
  const ackCount = allList.filter(a => a.status === 'acknowledged').length;
  const resolvedCount = allList.filter(a => a.status === 'resolved').length;
  const critCount = allList.filter(a => a.severity === 'critical' && a.status !== 'resolved').length;

  document.getElementById('alertKpiActive').textContent = activeCount;
  document.getElementById('alertKpiAck').textContent = ackCount;
  document.getElementById('alertKpiResolved').textContent = resolvedCount;
  document.getElementById('alertKpiCritical').textContent = critCount;
}

function setAlertStatusFilter(status, btn) {
  activeStatusFilter = status;
  document.querySelectorAll('.tabs-group .tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  fetchAlerts();
}

function onSeverityChange() {
  const select = document.getElementById('alertSeveritySelect');
  activeSeverityFilter = select.value;
  fetchAlerts();
}

function renderAlertsTable() {
  const tbody = document.getElementById('alertsTableBody');
  if (!tbody) return;

  if (currentAlerts.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="empty-state" style="color: var(--accent-green); padding: 40px 0;">
          <div class="empty-state-icon">✓</div>
          <div>No incidents found for the selected filter. Infrastructure operating within normal parameters.</div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = currentAlerts.map(a => {
    const sevBadge = a.severity === 'critical'
      ? `<span class="badge badge-critical">CRITICAL</span>`
      : `<span class="badge badge-warning">WARNING</span>`;

    const statusBadge = `<span class="badge badge-${a.status}">${a.status.toUpperCase()}</span>`;

    let readingDisplay = '--';
    if (a.alert_type === 'OFFLINE') {
      readingDisplay = `<span style="color: var(--accent-red); font-weight: 600;">Unreachable</span>`;
    } else if (a.metric_value !== null && a.metric_value !== undefined) {
      readingDisplay = `<code>${a.metric_value.toFixed(1)}% / ${a.threshold_value}%</code>`;
    }

    let actionsHtml = '';
    if (a.status === 'active') {
      actionsHtml = `
        <button class="btn btn-warning btn-sm" onclick="handleAcknowledge(${a.id})">Acknowledge</button>
        <button class="btn btn-success btn-sm" onclick="handleResolve(${a.id})">Resolve</button>
      `;
    } else if (a.status === 'acknowledged') {
      actionsHtml = `
        <button class="btn btn-success btn-sm" onclick="handleResolve(${a.id})">Resolve</button>
      `;
    } else {
      actionsHtml = `<span style="font-size: 0.8rem; color: var(--text-muted);">Resolved</span>`;
    }

    return `
      <tr>
        <td>${sevBadge}</td>
        <td><span class="badge badge-info">${a.alert_type}</span></td>
        <td><strong>${a.server_name}</strong></td>
        <td>${a.description}</td>
        <td>${readingDisplay}</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${a.created_at}</td>
        <td>${statusBadge}</td>
        <td style="text-align: right;">
          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            ${actionsHtml}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function handleAcknowledge(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('Incident acknowledged by admin.', 'warning');
      fetchAlerts();
    } else {
      showToast(data.error || 'Failed to acknowledge alert.', 'danger');
    }
  } catch (err) {
    showToast('Network error while acknowledging alert.', 'danger');
  }
}

async function handleResolve(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/resolve`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('Incident resolved successfully.', 'success');
      fetchAlerts();
    } else {
      showToast(data.error || 'Failed to resolve alert.', 'danger');
    }
  } catch (err) {
    showToast('Network error while resolving alert.', 'danger');
  }
}
