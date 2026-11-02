from django.contrib import admin
from .models import Server, MetricHistory, Alert, SystemLog, Setting

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'is_local', 'status', 'cpu_cores', 'total_ram_gb', 'last_heartbeat')
    list_filter = ('status', 'is_local')
    search_fields = ('name', 'ip_address', 'hostname')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'server_name', 'alert_type', 'severity', 'status', 'created_at')
    list_filter = ('severity', 'status', 'alert_type')
    search_fields = ('server_name', 'description')

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'server_name', 'event_type', 'severity')
    list_filter = ('severity', 'event_type')
    search_fields = ('server_name', 'description')

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('cpu_warning', 'cpu_critical', 'ram_warning', 'ram_critical', 'disk_warning', 'polling_interval')
