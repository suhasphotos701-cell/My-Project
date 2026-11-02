import time
import math
import random
import threading
import platform
import socket
import os
import psutil
from datetime import datetime

class MonitoringEngine:
    def __init__(self):
        self.running = False
        self.thread = None
        
        # Network snapshot tracking
        self.last_net_time = time.time()
        try:
            net_io = psutil.net_io_counters()
            self.last_bytes_sent = net_io.bytes_sent
            self.last_bytes_recv = net_io.bytes_recv
        except Exception:
            self.last_bytes_sent = 0
            self.last_bytes_recv = 0
            
        self.simulated_states = {}
        self.lock = threading.Lock()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def init_seed_data(self):
        """Seed initial database rows if empty."""
        from .models import Server, Setting, SystemLog

        # Ensure default setting exists
        Setting.objects.get_or_create(
            id=1,
            defaults={
                'cpu_warning': 80.0,
                'cpu_critical': 90.0,
                'ram_warning': 85.0,
                'ram_critical': 95.0,
                'disk_warning': 90.0,
                'polling_interval': 3
            }
        )

        # Ensure local server exists
        if not Server.objects.filter(is_local=True).exists():
            hname = socket.gethostname()
            os_desc = f"{platform.system()} {platform.release()}"
            Server.objects.create(
                name=f"{hname} (Local Host)",
                ip_address="127.0.0.1",
                hostname=hname,
                os_info=os_desc,
                is_local=True,
                status="online",
                simulated_profile="local",
                cpu_cores=psutil.cpu_count(logical=True) or 4
            )

        # Seed simulated cluster nodes if none exist
        if not Server.objects.filter(is_local=False).exists():
            nodes = [
                ("US-East-App-01 (Simulated)", "192.168.1.101", "app01.serverpulse.internal", "Linux Ubuntu 22.04 LTS", "web_server", 8, 32.0, 500.0),
                ("DB-Primary-Node (Simulated)", "192.168.1.102", "postgres-primary.internal", "Red Hat Enterprise Linux 9", "database", 16, 64.0, 1000.0),
                ("Backup-Storage-01 (Simulated)", "192.168.1.105", "backup.serverpulse.internal", "Debian 12 Bookworm", "storage", 4, 16.0, 2000.0)
            ]
            for name, ip, host, os_desc, profile, cores, ram, disk in nodes:
                Server.objects.create(
                    name=name, ip_address=ip, hostname=host, os_info=os_desc,
                    is_local=False, status="online", simulated_profile=profile,
                    cpu_cores=cores, total_ram_gb=ram, total_disk_gb=disk
                )

        # Initial logs
        if SystemLog.objects.count() == 0:
            SystemLog.objects.create(server_name="System", event_type="STARTUP", description="ServerPulse Django monitoring engine initialized.", severity="info")
            SystemLog.objects.create(server_name="Local Host", event_type="DISCOVERY", description="Local host telemetry connected via Psutil.", severity="info")
            SystemLog.objects.create(server_name="Cluster", event_type="SYNC", description="Simulated cluster telemetry pool online.", severity="info")

    def _get_local_metrics(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_cores = psutil.cpu_count(logical=True) or 1

            mem = psutil.virtual_memory()
            ram_percent = mem.percent
            ram_total_gb = round(mem.total / (1024 ** 3), 2)
            ram_used_gb = round(mem.used / (1024 ** 3), 2)
            ram_available_gb = round(mem.available / (1024 ** 3), 2)

            root_path = os.path.abspath(os.sep)
            if platform.system() == 'Windows':
                root_path = os.path.splitdrive(os.getcwd())[0] + '\\'
            disk = psutil.disk_usage(root_path)
            disk_percent = disk.percent
            disk_total_gb = round(disk.total / (1024 ** 3), 2)
            disk_used_gb = round(disk.used / (1024 ** 3), 2)
            disk_free_gb = round(disk.free / (1024 ** 3), 2)

            now = time.time()
            elapsed = max(now - self.last_net_time, 0.001)
            net_io = psutil.net_io_counters()
            sent_diff = max(net_io.bytes_sent - self.last_bytes_sent, 0)
            recv_diff = max(net_io.bytes_recv - self.last_bytes_recv, 0)

            self.last_net_time = now
            self.last_bytes_sent = net_io.bytes_sent
            self.last_bytes_recv = net_io.bytes_recv

            net_sent_rate = round(sent_diff / (1024 * elapsed), 2)
            net_recv_rate = round(recv_diff / (1024 * elapsed), 2)
            uptime_seconds = int(time.time() - psutil.boot_time())

            return {
                'cpu_percent': cpu_percent,
                'cpu_cores': cpu_cores,
                'ram_percent': ram_percent,
                'ram_total_gb': ram_total_gb,
                'ram_used_gb': ram_used_gb,
                'ram_available_gb': ram_available_gb,
                'disk_percent': disk_percent,
                'disk_total_gb': disk_total_gb,
                'disk_used_gb': disk_used_gb,
                'disk_free_gb': disk_free_gb,
                'net_sent_rate': net_sent_rate,
                'net_recv_rate': net_recv_rate,
                'uptime_seconds': uptime_seconds
            }
        except Exception as e:
            print(f"Error reading local psutil metrics: {e}")
            return None

    def _get_simulated_metrics(self, server_id, profile, cores, ram_gb, disk_gb):
        with self.lock:
            state = self.simulated_states.get(server_id)
            if not state:
                base_cpu = 25.0 if profile == 'web_server' else (45.0 if profile == 'database' else 15.0)
                base_ram = 50.0 if profile == 'web_server' else (65.0 if profile == 'database' else 30.0)
                base_disk = 60.0 if profile == 'storage' else 45.0
                state = {
                    'cpu': base_cpu,
                    'ram': base_ram,
                    'disk': base_disk,
                    'step': random.randint(0, 100),
                    'spike_cpu': 0.0,
                    'spike_ram': 0.0,
                    'spike_cycles': 0
                }
                self.simulated_states[server_id] = state

            spike_cpu = state.get('spike_cpu', 0.0)
            spike_ram = state.get('spike_ram', 0.0)
            if state.get('spike_cycles', 0) > 0:
                state['spike_cycles'] -= 1
            else:
                state['spike_cpu'] = 0.0
                state['spike_ram'] = 0.0

            state['step'] += 1
            step = state['step']

            cpu_fluct = math.sin(step / 6.0) * 8.0 + random.uniform(-3.0, 3.0)
            ram_fluct = math.cos(step / 10.0) * 3.0 + random.uniform(-1.0, 1.0)
            disk_fluct = random.uniform(0.0, 0.04)

            current_cpu = max(5.0, min(99.0, state['cpu'] + cpu_fluct + spike_cpu))
            current_ram = max(10.0, min(98.0, state['ram'] + ram_fluct + spike_ram))
            current_disk = max(10.0, min(95.0, state['disk'] + disk_fluct))
            state['disk'] = current_disk

            if profile == 'web_server':
                net_sent = round(random.uniform(400.0, 2500.0) + (current_cpu * 15.0), 2)
                net_recv = round(random.uniform(200.0, 1200.0) + (current_cpu * 8.0), 2)
            elif profile == 'database':
                net_sent = round(random.uniform(300.0, 1800.0), 2)
                net_recv = round(random.uniform(500.0, 2200.0), 2)
            else:
                net_sent = round(random.uniform(50.0, 400.0), 2)
                net_recv = round(random.uniform(50.0, 500.0), 2)

            used_ram = round((current_ram / 100.0) * ram_gb, 2)
            used_disk = round((current_disk / 100.0) * disk_gb, 2)

            return {
                'cpu_percent': round(current_cpu, 1),
                'cpu_cores': cores,
                'ram_percent': round(current_ram, 1),
                'ram_total_gb': ram_gb,
                'ram_used_gb': used_ram,
                'ram_available_gb': round(ram_gb - used_ram, 2),
                'disk_percent': round(current_disk, 1),
                'disk_total_gb': disk_gb,
                'disk_used_gb': used_disk,
                'disk_free_gb': round(disk_gb - used_disk, 2),
                'net_sent_rate': net_sent,
                'net_recv_rate': net_recv,
                'uptime_seconds': 86400 * 3 + step * 4
            }

    def trigger_spike(self, server_id, cpu_val=92.0, ram_val=88.0, duration_cycles=6):
        with self.lock:
            if server_id not in self.simulated_states:
                self.simulated_states[server_id] = {'cpu': 30.0, 'ram': 40.0, 'disk': 50.0, 'step': 0}
            self.simulated_states[server_id]['spike_cpu'] = cpu_val
            self.simulated_states[server_id]['spike_ram'] = ram_val
            self.simulated_states[server_id]['spike_cycles'] = duration_cycles

    def _process_alerts(self, server, metrics, settings):
        from .models import Alert, SystemLog

        server_id = server.id
        server_name = server.name
        is_online = (server.status == 'online')

        if not is_online:
            offline_alert = Alert.objects.filter(server=server, alert_type='OFFLINE', status__in=['active', 'acknowledged']).first()
            if not offline_alert:
                Alert.objects.create(
                    server=server,
                    server_name=server_name,
                    alert_type='OFFLINE',
                    severity='critical',
                    description=f"Server '{server_name}' is offline / unresponsive!",
                    metric_value=0.0,
                    threshold_value=1.0,
                    status='active'
                )
                SystemLog.objects.create(
                    server_name=server_name,
                    event_type="ALERT_TRIGGERED",
                    description=f"Server '{server_name}' went OFFLINE. Critical alert generated.",
                    severity="critical"
                )
            return
        else:
            active_offlines = Alert.objects.filter(server=server, alert_type='OFFLINE', status__in=['active', 'acknowledged'])
            for off in active_offlines:
                off.status = 'resolved'
                off.resolved_at = datetime.now()
                off.save()
                SystemLog.objects.create(
                    server_name=server_name,
                    event_type="ALERT_RESOLVED",
                    description=f"Server '{server_name}' is back online. Offline alert resolved.",
                    severity="info"
                )

        if not metrics:
            return

        checks = [
            {'type': 'CPU', 'val': metrics['cpu_percent'], 'warn': settings.cpu_warning, 'crit': settings.cpu_critical},
            {'type': 'RAM', 'val': metrics['ram_percent'], 'warn': settings.ram_warning, 'crit': settings.ram_critical},
            {'type': 'DISK', 'val': metrics['disk_percent'], 'warn': settings.disk_warning, 'crit': settings.disk_warning}
        ]

        for check in checks:
            alert_type = check['type']
            val = check['val']
            warn_th = check['warn']
            crit_th = check['crit']

            severity = None
            threshold_hit = None
            if val >= crit_th:
                severity = 'critical'
                threshold_hit = crit_th
            elif val >= warn_th:
                severity = 'warning'
                threshold_hit = warn_th

            existing_alert = Alert.objects.filter(server=server, alert_type=alert_type, status__in=['active', 'acknowledged']).first()

            if severity:
                desc = f"{alert_type} utilization reached {val:.1f}% (Threshold: {threshold_hit:.1f}%)"
                if not existing_alert:
                    Alert.objects.create(
                        server=server,
                        server_name=server_name,
                        alert_type=alert_type,
                        severity=severity,
                        description=desc,
                        metric_value=val,
                        threshold_value=threshold_hit,
                        status='active'
                    )
                    SystemLog.objects.create(
                        server_name=server_name,
                        event_type=f"{alert_type.upper()}_ALERT",
                        description=desc,
                        severity=severity
                    )
                else:
                    if existing_alert.severity != severity and severity == 'critical':
                        existing_alert.severity = 'critical'
                        existing_alert.description = desc
                        existing_alert.metric_value = val
                        existing_alert.threshold_value = threshold_hit
                        existing_alert.save()
                        SystemLog.objects.create(
                            server_name=server_name,
                            event_type="ALERT_ESCALATION",
                            description=f"{server_name} {alert_type} alert escalated to CRITICAL ({val:.1f}%).",
                            severity="critical"
                        )
                    else:
                        existing_alert.description = desc
                        existing_alert.metric_value = val
                        existing_alert.save()
            else:
                if existing_alert:
                    existing_alert.status = 'resolved'
                    existing_alert.resolved_at = datetime.now()
                    existing_alert.save()
                    SystemLog.objects.create(
                        server_name=server_name,
                        event_type="ALERT_RESOLVED",
                        description=f"{alert_type} usage normalized to {val:.1f}% on {server_name}. Alert resolved.",
                        severity="info"
                    )

    def _collect_and_store_cycle(self):
        from .models import Server, MetricHistory, Setting
        from django.db import connection

        try:
            self.init_seed_data()
            settings = Setting.objects.first()
            if not settings:
                return

            servers = list(Server.objects.all())

            for s in servers:
                if s.status == 'offline':
                    self._process_alerts(s, None, settings)
                    continue

                metrics = None
                if s.is_local:
                    metrics = self._get_local_metrics()
                    if metrics:
                        s.cpu_cores = metrics['cpu_cores']
                        s.total_ram_gb = metrics['ram_total_gb']
                        s.total_disk_gb = metrics['disk_total_gb']
                        s.save(update_fields=['cpu_cores', 'total_ram_gb', 'total_disk_gb', 'last_heartbeat'])
                else:
                    metrics = self._get_simulated_metrics(s.id, s.simulated_profile, s.cpu_cores, s.total_ram_gb, s.total_disk_gb)
                    s.save(update_fields=['last_heartbeat'])

                if metrics:
                    MetricHistory.objects.create(
                        server=s,
                        cpu_percent=metrics['cpu_percent'],
                        ram_percent=metrics['ram_percent'],
                        ram_used_gb=metrics['ram_used_gb'],
                        ram_total_gb=metrics['ram_total_gb'],
                        disk_percent=metrics['disk_percent'],
                        disk_used_gb=metrics['disk_used_gb'],
                        disk_total_gb=metrics['disk_total_gb'],
                        net_bytes_sent_rate=metrics['net_sent_rate'],
                        net_bytes_recv_rate=metrics['net_recv_rate'],
                        uptime_seconds=metrics['uptime_seconds']
                    )
                    self._process_alerts(s, metrics, settings)

            # Prune older metrics: keep last 250 records per server
            for s in servers:
                excess_ids = list(MetricHistory.objects.filter(server=s).order_by('-id').values_list('id', flat=True)[250:])
                if excess_ids:
                    MetricHistory.objects.filter(id__in=excess_ids).delete()

        except Exception as e:
            print(f"Error in Django monitoring cycle: {e}")
        finally:
            connection.close()

    def _run_loop(self):
        psutil.cpu_percent(interval=None)
        while self.running:
            try:
                self._collect_and_store_cycle()
            except Exception as e:
                print(f"Exception in monitoring loop: {e}")

            interval = 3
            try:
                from .models import Setting
                s = Setting.objects.first()
                if s:
                    interval = max(2, min(10, s.polling_interval))
            except Exception:
                pass

            for _ in range(interval * 2):
                if not self.running:
                    break
                time.sleep(0.5)

engine = MonitoringEngine()

def start_monitoring():
    engine.start()
