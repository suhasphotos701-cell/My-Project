from django.urls import path
from . import views

urlpatterns = [
    # Frontend Pages
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard_alt'),
    path('servers/', views.servers_view, name='servers'),
    path('performance/', views.performance_view, name='performance'),
    path('alerts/', views.alerts_view, name='alerts'),
    path('logs/', views.logs_view, name='logs'),
    path('settings/', views.settings_view, name='settings'),

    # REST APIs
    path('api/dashboard', views.api_dashboard, name='api_dashboard'),
    path('api/metrics/current', views.api_current_metrics, name='api_current_metrics'),
    path('api/metrics/history', views.api_metrics_history, name='api_metrics_history'),
    path('api/servers', views.api_servers, name='api_servers'),
    path('api/servers/<int:server_id>', views.api_delete_server, name='api_delete_server'),
    path('api/servers/<int:server_id>/toggle-status', views.api_toggle_server_status, name='api_toggle_server_status'),
    path('api/servers/<int:server_id>/spike', views.api_spike_server, name='api_spike_server'),
    path('api/alerts', views.api_alerts, name='api_alerts'),
    path('api/alerts/<int:alert_id>/acknowledge', views.api_acknowledge_alert, name='api_acknowledge_alert'),
    path('api/alerts/<int:alert_id>/resolve', views.api_resolve_alert, name='api_resolve_alert'),
    path('api/logs', views.api_logs, name='api_logs'),
    path('api/settings', views.api_settings, name='api_settings'),
]
