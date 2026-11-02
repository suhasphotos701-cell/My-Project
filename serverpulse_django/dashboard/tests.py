import json
from django.test import TestCase, Client
from django.urls import reverse
from .models import Server, MetricHistory, Alert, SystemLog, Setting
from .monitoring import engine

class ServerPulseDjangoTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed test data
        engine.init_seed_data()
        engine._collect_and_store_cycle()

    def test_01_pages_render_successfully(self):
        urls = ['dashboard', 'servers', 'performance', 'alerts', 'logs', 'settings']
        for u in urls:
            res = self.client.get(reverse(u))
            self.assertEqual(res.status_code, 200, f"Page {u} failed to render")
            self.assertContains(res, "ServerPulse")

    def test_02_api_dashboard(self):
        res = self.client.get(reverse('api_dashboard'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('total_servers', data)
        self.assertIn('online_servers', data)
        self.assertIn('avg_cpu', data)
        self.assertIn('servers', data)
        self.assertGreaterEqual(data['total_servers'], 1)

    def test_03_server_crud_and_status_toggle(self):
        # 1. Add new server
        payload = {
            'name': 'Test-Django-App-01',
            'ip_address': '10.0.0.55',
            'hostname': 'django.internal',
            'os_info': 'Ubuntu 24.04',
            'simulated_profile': 'web_server',
            'cpu_cores': 8,
            'total_ram_gb': 32.0,
            'total_disk_gb': 500.0
        }
        res = self.client.post(reverse('api_servers'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        server_id = data['server_id']

        # 2. Toggle status
        toggle_res = self.client.post(reverse('api_toggle_server_status', args=[server_id]))
        self.assertEqual(toggle_res.status_code, 200)
        self.assertEqual(toggle_res.json()['new_status'], 'offline')

        # Toggle back online
        toggle_res2 = self.client.post(reverse('api_toggle_server_status', args=[server_id]))
        self.assertEqual(toggle_res2.status_code, 200)
        self.assertEqual(toggle_res2.json()['new_status'], 'online')

        # 3. Simulate spike
        spike_res = self.client.post(reverse('api_spike_server', args=[server_id]), data=json.dumps({'cpu': 95.0, 'ram': 91.0, 'cycles': 3}), content_type='application/json')
        self.assertEqual(spike_res.status_code, 200)

        # 4. Delete server
        del_res = self.client.delete(reverse('api_delete_server', args=[server_id]))
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()['success'])

    def test_04_api_metrics_history(self):
        res = self.client.get(reverse('api_metrics_history'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('labels', data)
        self.assertIn('cpu', data)
        self.assertIn('ram', data)
        self.assertIn('disk', data)

    def test_05_alerts_lifecycle(self):
        alerts_res = self.client.get(reverse('api_alerts') + '?status=all')
        self.assertEqual(alerts_res.status_code, 200)
        alerts = alerts_res.json()
        self.assertIsInstance(alerts, list)

        # Create test alert to verify acknowledge and resolve
        server = Server.objects.first()
        alert = Alert.objects.create(
            server=server,
            server_name=server.name,
            alert_type='CPU',
            severity='warning',
            description='Test warning alert',
            metric_value=84.5,
            threshold_value=80.0,
            status='active'
        )

        ack_res = self.client.post(reverse('api_acknowledge_alert', args=[alert.id]))
        self.assertEqual(ack_res.status_code, 200)
        alert.refresh_from_db()
        self.assertEqual(alert.status, 'acknowledged')

        res_res = self.client.post(reverse('api_resolve_alert', args=[alert.id]))
        self.assertEqual(res_res.status_code, 200)
        alert.refresh_from_db()
        self.assertEqual(alert.status, 'resolved')

    def test_06_settings_get_and_post(self):
        res = self.client.get(reverse('api_settings'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('cpu_warning', data)

        post_data = {
            'cpu_warning': 72.0,
            'cpu_critical': 89.0,
            'ram_warning': 81.0,
            'ram_critical': 93.0,
            'disk_warning': 88.0,
            'polling_interval': 4
        }
        post_res = self.client.post(reverse('api_settings'), data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(post_res.status_code, 200)
        self.assertTrue(post_res.json()['success'])

        setting = Setting.objects.first()
        self.assertEqual(setting.cpu_warning, 72.0)

    def test_07_logs_query(self):
        res = self.client.get(reverse('api_logs') + '?limit=50')
        self.assertEqual(res.status_code, 200)
        logs = res.json()
        self.assertIsInstance(logs, list)
        self.assertGreater(len(logs), 0)
