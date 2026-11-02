from django.db import models

class Server(models.Model):
    name = models.CharField(max_length=150)
    ip_address = models.CharField(max_length=50)
    hostname = models.CharField(max_length=150, blank=True)
    os_info = models.CharField(max_length=150, default='Linux Ubuntu 22.04 LTS')
    is_local = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='online')  # 'online', 'offline'
    simulated_profile = models.CharField(max_length=50, default='balanced')
    cpu_cores = models.IntegerField(default=4)
    total_ram_gb = models.FloatField(default=16.0)
    total_disk_gb = models.FloatField(default=500.0)
    last_heartbeat = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_local', 'id']

    def __str__(self):
        return f"{self.name} ({self.ip_address})"


class MetricHistory(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='metrics')
    timestamp = models.DateTimeField(auto_now_add=True)
    cpu_percent = models.FloatField()
    ram_percent = models.FloatField()
    ram_used_gb = models.FloatField()
    ram_total_gb = models.FloatField()
    disk_percent = models.FloatField()
    disk_used_gb = models.FloatField()
    disk_total_gb = models.FloatField()
    net_bytes_sent_rate = models.FloatField(default=0.0)  # KB/s
    net_bytes_recv_rate = models.FloatField(default=0.0)  # KB/s
    uptime_seconds = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['server', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.server.name} @ {self.timestamp}: CPU {self.cpu_percent}%"


class Alert(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='alerts')
    server_name = models.CharField(max_length=150)
    alert_type = models.CharField(max_length=50)  # 'CPU', 'RAM', 'DISK', 'OFFLINE'
    severity = models.CharField(max_length=20)    # 'warning', 'critical'
    description = models.TextField()
    metric_value = models.FloatField(null=True, blank=True)
    threshold_value = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active')  # 'active', 'acknowledged', 'resolved'
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['server', 'alert_type', 'status']),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.server_name} - {self.alert_type} ({self.status})"


class SystemLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    server_name = models.CharField(max_length=150, default='System')
    event_type = models.CharField(max_length=50)
    description = models.TextField()
    severity = models.CharField(max_length=20, default='info')  # 'info', 'warning', 'critical'

    class Meta:
        ordering = ['-id']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.event_type}: {self.description[:40]}"


class Setting(models.Model):
    cpu_warning = models.FloatField(default=80.0)
    cpu_critical = models.FloatField(default=90.0)
    ram_warning = models.FloatField(default=85.0)
    ram_critical = models.FloatField(default=95.0)
    disk_warning = models.FloatField(default=90.0)
    polling_interval = models.IntegerField(default=3)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings: CPU({self.cpu_warning}/{self.cpu_critical}), RAM({self.ram_warning}/{self.ram_critical})"
