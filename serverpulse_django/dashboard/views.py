import json
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Avg
from .models import Server, MetricHistory, Alert, SystemLog, Setting
from .monitoring import engine

# -------------------------------------------------------------
# Frontend Page Views
# -------------------------------------------------------------

def dashboard_view(request):
    return render(request, 'dashboard.html', {'active_page': 'dashboard'})

def servers_view(request):
    return render(request, 'servers.html', {'active_page': 'servers'})

def performance_view(request):
    return render(request, 'performance.html', {'active_page': 'performance'})

def alerts_view(request):
    return render(request, 'alerts.html', {'active_page': 'alerts'})

def logs_view(request):
    return render(request, 'logs.html', {'active_page': 'logs'})

def settings_view(request):
    return render(request, 'settings.html', {'active_page': 'settings'})


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

def api_dashboard(request):
    servers = list(Server.objects.all())
    total_servers = len(servers)
    online_servers = sum(1 for s in servers if s.status == 'online')
    offline_servers = total_servers - online_servers

    server_list = []
    cpu_vals = []
    ram_vals = []

    for s in servers:
        latest = MetricHistory.objects.filter(server=s).order_by('-id').first()
        s_dict = {
            'id': s.id,
            'name': s.name,
            'ip_address': s.ip_address,
            'hostname': s.hostname,
            'os_info': s.os_info,
            'is_local': 1 if s.is_local else 0,
            'status': s.status,
            'simulated_profile': s.simulated_profile,
            'cpu_cores': s.cpu_cores,
            'total_ram_gb': s.total_ram_gb,
            'total_disk_gb': s.total_disk_gb,
            'last_heartbeat': s.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S') if s.last_heartbeat else None,
            'latest_metric': None
        }

        if latest and s.status == 'online':
            s_dict['latest_metric'] = {
                'cpu_percent': latest.cpu_percent,
                'ram_percent': latest.ram_percent,
                'disk_percent': latest.disk_percent,
                'net_bytes_sent_rate': latest.net_bytes_sent_rate,
                'net_bytes_recv_rate': latest.net_bytes_recv_rate,
                'uptime_seconds': latest.uptime_seconds,
            }
            cpu_vals.append(latest.cpu_percent)
            ram_vals.append(latest.ram_percent)

        server_list.append(s_dict)

    avg_cpu = round(sum(cpu_vals) / len(cpu_vals), 1) if cpu_vals else 0.0
    avg_ram = round(sum(ram_vals) / len(ram_vals), 1) if ram_vals else 0.0

    active_alerts_count = Alert.objects.filter(status__in=['active', 'acknowledged']).count()

    recent_alerts_qs = Alert.objects.filter(status__in=['active', 'acknowledged']).order_by('-id')[:6]
    recent_alerts = []
    for a in recent_alerts_qs:
        recent_alerts.append({
            'id': a.id,
            'server_name': a.server_name,
            'alert_type': a.alert_type,
            'severity': a.severity,
            'description': a.description,
            'metric_value': a.metric_value,
            'threshold_value': a.threshold_value,
            'status': a.status,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    return JsonResponse({
        'total_servers': total_servers,
        'online_servers': online_servers,
        'offline_servers': offline_servers,
        'avg_cpu': avg_cpu,
        'avg_ram': avg_ram,
        'active_alerts': active_alerts_count,
        'servers': server_list,
        'recent_alerts': recent_alerts
    })


def api_current_metrics(request):
    servers = Server.objects.all()
    results = []
    for s in servers:
        latest = MetricHistory.objects.filter(server=s).order_by('-id').first()
        m_dict = None
        if latest:
            m_dict = {
                'cpu_percent': latest.cpu_percent,
                'ram_percent': latest.ram_percent,
                'disk_percent': latest.disk_percent,
                'net_sent_rate': latest.net_bytes_sent_rate,
                'net_recv_rate': latest.net_bytes_recv_rate
            }
        results.append({
            'server': {
                'id': s.id,
                'name': s.name,
                'status': s.status,
                'is_local': s.is_local
            },
            'metric': m_dict
        })
    return JsonResponse(results, safe=False)


def api_metrics_history(request):
    server_id = request.GET.get('server_id')
    limit = int(request.GET.get('limit', 30))
    limit = max(10, min(100, limit))

    if server_id:
        server = Server.objects.filter(id=server_id).first()
    else:
        server = Server.objects.order_by('-is_local', 'id').first()

    if not server:
        return JsonResponse({'labels': [], 'cpu': [], 'ram': [], 'net_sent': [], 'net_recv': [], 'disk': {}})

    server_info = {
        'id': server.id,
        'name': server.name,
        'ip_address': server.ip_address,
        'cpu_cores': server.cpu_cores,
        'total_ram_gb': server.total_ram_gb,
        'total_disk_gb': server.total_disk_gb
    }

    metrics_qs = list(MetricHistory.objects.filter(server=server).order_by('-id')[:limit])
    metrics_qs.reverse()

    labels = []
    cpu_series = []
    ram_series = []
    net_sent_series = []
    net_recv_series = []
    last_disk_info = {
        'percent': 0,
        'used_gb': 0,
        'total_gb': server.total_disk_gb,
        'free_gb': 0
    }

    for m in metrics_qs:
        labels.append(m.timestamp.strftime('%H:%M:%S'))
        cpu_series.append(m.cpu_percent)
        ram_series.append(m.ram_percent)
        net_sent_series.append(m.net_bytes_sent_rate)
        net_recv_series.append(m.net_bytes_recv_rate)
        last_disk_info = {
            'percent': m.disk_percent,
            'used_gb': m.disk_used_gb,
            'total_gb': m.disk_total_gb,
            'free_gb': round(m.disk_total_gb - m.disk_used_gb, 2)
        }

    return JsonResponse({
        'server': server_info,
        'labels': labels,
        'cpu': cpu_series,
        'ram': ram_series,
        'net_sent': net_sent_series,
        'net_recv': net_recv_series,
        'disk': last_disk_info
    })


@csrf_exempt
def api_servers(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')

        name = data.get('name', '').strip()
        ip = data.get('ip_address', '').strip()
        hostname = data.get('hostname', '').strip()
        os_info = data.get('os_info', 'Linux Ubuntu 22.04 LTS').strip()
        profile = data.get('simulated_profile', 'web_server')
        cores = int(data.get('cpu_cores', 4))
        ram = float(data.get('total_ram_gb', 16.0))
        disk = float(data.get('total_disk_gb', 500.0))

        if not name or not ip:
            return JsonResponse({'success': False, 'error': 'Server name and IP address are required.'}, status=400)

        server = Server.objects.create(
            name=name,
            ip_address=ip,
            hostname=hostname or ip,
            os_info=os_info,
            simulated_profile=profile,
            cpu_cores=cores,
            total_ram_gb=ram,
            total_disk_gb=disk,
            is_local=False,
            status='online'
        )

        SystemLog.objects.create(
            server_name=name,
            event_type="SERVER_ADDED",
            description=f"New server '{name}' ({ip}) registered to cluster.",
            severity="info"
        )

        return JsonResponse({'success': True, 'server_id': server.id, 'message': f"Server '{name}' added successfully."})

    # GET
    servers = Server.objects.all()
    server_list = []
    for s in servers:
        latest = MetricHistory.objects.filter(server=s).order_by('-id').first()
        m_dict = None
        if latest and s.status == 'online':
            m_dict = {
                'cpu_percent': latest.cpu_percent,
                'ram_percent': latest.ram_percent,
                'disk_percent': latest.disk_percent,
                'uptime_seconds': latest.uptime_seconds
            }

        server_list.append({
            'id': s.id,
            'name': s.name,
            'ip_address': s.ip_address,
            'hostname': s.hostname,
            'os_info': s.os_info,
            'is_local': 1 if s.is_local else 0,
            'status': s.status,
            'simulated_profile': s.simulated_profile,
            'cpu_cores': s.cpu_cores,
            'total_ram_gb': s.total_ram_gb,
            'total_disk_gb': s.total_disk_gb,
            'last_heartbeat': s.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S') if s.last_heartbeat else None,
            'latest_metric': m_dict
        })
    return JsonResponse(server_list, safe=False)


@csrf_exempt
def api_delete_server(request, server_id):
    if request.method != 'DELETE':
        return HttpResponseBadRequest('Method not allowed')

    server = Server.objects.filter(id=server_id).first()
    if not server:
        return JsonResponse({'success': False, 'error': 'Server not found.'}, status=404)

    if server.is_local:
        return JsonResponse({'success': False, 'error': 'Cannot delete the primary local host machine.'}, status=400)

    name = server.name
    server.delete()

    SystemLog.objects.create(
        server_name=name,
        event_type="SERVER_REMOVED",
        description=f"Server '{name}' was removed from dashboard.",
        severity="warning"
    )

    return JsonResponse({'success': True, 'message': f"Server '{name}' deleted successfully."})


@csrf_exempt
def api_toggle_server_status(request, server_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('Method not allowed')

    server = Server.objects.filter(id=server_id).first()
    if not server:
        return JsonResponse({'success': False, 'error': 'Server not found.'}, status=404)

    new_status = 'offline' if server.status == 'online' else 'online'
    server.status = new_status
    server.save(update_fields=['status'])

    evt_type = "SERVER_DISCONNECTED" if new_status == 'offline' else "SERVER_CONNECTED"
    severity = "critical" if new_status == 'offline' else "info"
    SystemLog.objects.create(
        server_name=server.name,
        event_type=evt_type,
        description=f"Server '{server.name}' status changed to {new_status.upper()}.",
        severity=severity
    )

    return JsonResponse({'success': True, 'new_status': new_status, 'message': f"Server '{server.name}' is now {new_status}."})


@csrf_exempt
def api_spike_server(request, server_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('Method not allowed')

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = {}

    cpu = float(data.get('cpu', 94.0))
    ram = float(data.get('ram', 89.0))
    cycles = int(data.get('cycles', 6))

    engine.trigger_spike(server_id, cpu_val=cpu, ram_val=ram, duration_cycles=cycles)
    SystemLog.objects.create(
        server_name=f"Server #{server_id}",
        event_type="SIMULATION_SPIKE",
        description=f"Simulated load spike triggered on Server ID #{server_id} (CPU: {cpu}%, RAM: {ram}%).",
        severity="warning"
    )

    return JsonResponse({'success': True, 'message': f"Load spike active for next {cycles * 3} seconds."})


def api_alerts(request):
    status_filter = request.GET.get('status', 'all')
    severity_filter = request.GET.get('severity', 'all')

    qs = Alert.objects.all()

    if status_filter in ['active', 'acknowledged', 'resolved']:
        qs = qs.filter(status=status_filter)
    elif status_filter == 'unresolved':
        qs = qs.filter(status__in=['active', 'acknowledged'])

    if severity_filter in ['warning', 'critical']:
        qs = qs.filter(severity=severity_filter)

    alerts = []
    for a in qs[:150]:
        alerts.append({
            'id': a.id,
            'server_name': a.server_name,
            'alert_type': a.alert_type,
            'severity': a.severity,
            'description': a.description,
            'metric_value': a.metric_value,
            'threshold_value': a.threshold_value,
            'status': a.status,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'acknowledged_at': a.acknowledged_at.strftime('%Y-%m-%d %H:%M:%S') if a.acknowledged_at else None,
            'resolved_at': a.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if a.resolved_at else None,
        })
    return JsonResponse(alerts, safe=False)


@csrf_exempt
def api_acknowledge_alert(request, alert_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('Method not allowed')

    alert = Alert.objects.filter(id=alert_id).first()
    if not alert:
        return JsonResponse({'success': False, 'error': 'Alert not found.'}, status=404)

    alert.status = 'acknowledged'
    alert.acknowledged_at = datetime.now()
    alert.save(update_fields=['status', 'acknowledged_at'])

    SystemLog.objects.create(
        server_name=alert.server_name,
        event_type="ALERT_ACKNOWLEDGED",
        description=f"Alert #{alert_id} ({alert.alert_type} on {alert.server_name}) was acknowledged by admin.",
        severity="info"
    )

    return JsonResponse({'success': True, 'message': f"Alert #{alert_id} acknowledged."})


@csrf_exempt
def api_resolve_alert(request, alert_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('Method not allowed')

    alert = Alert.objects.filter(id=alert_id).first()
    if not alert:
        return JsonResponse({'success': False, 'error': 'Alert not found.'}, status=404)

    alert.status = 'resolved'
    alert.resolved_at = datetime.now()
    alert.save(update_fields=['status', 'resolved_at'])

    SystemLog.objects.create(
        server_name=alert.server_name,
        event_type="ALERT_RESOLVED",
        description=f"Alert #{alert_id} ({alert.alert_type} on {alert.server_name}) manually resolved.",
        severity="info"
    )

    return JsonResponse({'success': True, 'message': f"Alert #{alert_id} resolved."})


def api_logs(request):
    severity = request.GET.get('severity', 'all')
    search = request.GET.get('search', '').strip()
    limit = int(request.GET.get('limit', 100))

    qs = SystemLog.objects.all()

    if severity in ['info', 'warning', 'critical']:
        qs = qs.filter(severity=severity)

    if search:
        qs = qs.filter(Q(description__icontains=search) | Q(server_name__icontains=search) | Q(event_type__icontains=search))

    logs = []
    for l in qs[:limit]:
        logs.append({
            'id': l.id,
            'timestamp': l.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'server_name': l.server_name,
            'event_type': l.event_type,
            'description': l.description,
            'severity': l.severity
        })

    return JsonResponse(logs, safe=False)


@csrf_exempt
def api_settings(request):
    settings = Setting.objects.first()
    if not settings:
        settings = Setting.objects.create()

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')

        try:
            cpu_warn = float(data.get('cpu_warning', 80.0))
            cpu_crit = float(data.get('cpu_critical', 90.0))
            ram_warn = float(data.get('ram_warning', 85.0))
            ram_crit = float(data.get('ram_critical', 95.0))
            disk_warn = float(data.get('disk_warning', 90.0))
            interval = int(data.get('polling_interval', 3))

            if cpu_warn >= cpu_crit:
                return JsonResponse({'success': False, 'error': 'CPU Warning threshold must be lower than Critical threshold.'}, status=400)
            if ram_warn >= ram_crit:
                return JsonResponse({'success': False, 'error': 'RAM Warning threshold must be lower than Critical threshold.'}, status=400)

            settings.cpu_warning = cpu_warn
            settings.cpu_critical = cpu_crit
            settings.ram_warning = ram_warn
            settings.ram_critical = ram_crit
            settings.disk_warning = disk_warn
            settings.polling_interval = interval
            settings.save()

            SystemLog.objects.create(
                server_name="Settings",
                event_type="SETTINGS_UPDATED",
                description=f"Thresholds updated: CPU({cpu_warn}%/{cpu_crit}%), RAM({ram_warn}%/{ram_crit}%), Disk({disk_warn}%).",
                severity="info"
            )

            return JsonResponse({'success': True, 'message': 'Monitoring thresholds saved successfully.'})
        except ValueError as ve:
            return JsonResponse({'success': False, 'error': str(ve)}, status=400)

    return JsonResponse({
        'cpu_warning': settings.cpu_warning,
        'cpu_critical': settings.cpu_critical,
        'ram_warning': settings.ram_warning,
        'ram_critical': settings.ram_critical,
        'disk_warning': settings.disk_warning,
        'polling_interval': settings.polling_interval
    })
