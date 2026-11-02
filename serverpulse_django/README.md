# ServerPulse – Server Health Monitoring Dashboard (Django Edition)

A modern, functional, DevOps-styled server health monitoring web application built using **Django** and **psutil**. **ServerPulse** collects real-time hardware telemetry from the host machine using Python's `psutil` library, provides multi-server simulated cluster monitoring, visualizes resource trends using bundled `Chart.js`, and manages alerts with duplicate prevention and automatic resolution.

---

## 1. Technology Stack

- **Backend**: Python 3.10+, **Django 5.1+** (Django ORM, Views, Templates, Admin)
- **Telemetry**: `psutil` (collecting live CPU, RAM, Disk, and Network I/O from host OS)
- **Database**: SQLite 3 (`serverpulse.db` managed via Django migrations)
- **Frontend**: HTML5, CSS3 (Dark DevOps design system), JavaScript, **Chart.js 4.4** (bundled locally for 100% offline capability)

---

## 2. Project Directory Structure

```text
serverpulse_django/
├── manage.py                     # Django management CLI
├── requirements.txt               # Dependencies (Django, psutil)
├── README.md                      # Documentation & presentation guide
├── serverpulse.db                 # SQLite database (auto-created via migrations)
│
├── serverpulse/                   # Project Configuration
│   ├── __init__.py
│   ├── settings.py                # Django settings (DB, Static files, Apps)
│   ├── urls.py                    # Root URL router
│   ├── wsgi.py
│   └── asgi.py
│
├── dashboard/                     # Core Monitoring App
│   ├── __init__.py
│   ├── admin.py                   # Django Admin registrations
│   ├── apps.py                    # AppConfig & background telemetry launcher
│   ├── models.py                  # Server, MetricHistory, Alert, SystemLog, Setting
│   ├── monitoring.py              # Background psutil engine & alert logic
│   ├── views.py                   # HTML views & REST API endpoints
│   ├── urls.py                    # App routes & API endpoints
│   ├── tests.py                   # Automated test suite (7 tests)
│   └── migrations/
│       └── 0001_initial.py        # Django database schema migration
│
├── templates/                     # Django HTML Templates
│   ├── base.html                  # Master dark theme layout, sidebar, & header
│   ├── dashboard.html             # Overview dashboard (6 KPI cards, line charts)
│   ├── servers.html               # Server fleet table, modal forms, & controls
│   ├── performance.html           # Dedicated analytics & target server switcher
│   ├── alerts.html                # Incident management center
│   ├── logs.html                  # System audit log viewer
│   └── settings.html              # Alert threshold configuration
│
└── static/
    ├── css/
    │   └── style.css              # Dark DevOps stylesheet & animations
    └── js/
        ├── chart.min.js           # Bundled standalone Chart.js v4.4
        ├── dashboard.js           # Overview polling & Chart.js live sync
        ├── charts.js              # Dedicated performance analytics
        ├── servers.js             # Fleet table, modal forms, & toggle controls
        └── alerts.js              # Incident acknowledgement & resolution
```

---

## 3. How to Run in Visual Studio Code

### Step 1: Open in VS Code
1. Open **Visual Studio Code**.
2. Click **File** > **Open Folder...** and select the `serverpulse_django` folder:
   ```text
   C:\Users\suhas\.gemini\antigravity\scratch\serverpulse_django
   ```

### Step 2: Open the Terminal in VS Code
Press:
```text
Ctrl + `  (backtick)
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run Migrations (Already prepared, but good practice)
```powershell
python manage.py migrate
```

### Step 5: Start the Django Development Server
```powershell
python manage.py runserver
```

You will see:
```text
Watching for file changes with StatReloader
Performing system checks...
System check identified no issues (0 silenced).
Django version 5.1.1, using settings 'serverpulse.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Step 6: View the Dashboard in Your Browser
Open your browser and navigate to:
```text
http://127.0.0.1:8000
```

---

## 4. Key Features

- **Live Real-Time Host Telemetry**: CPU core count, CPU utilization %, RAM total/used/free, primary disk partition breakdown, network upload/download throughput in KB/s.
- **Multi-Server Management**: Clearly distinguishes between `[REAL HOST]` (measured via psutil) and `[SIMULATED]` nodes (custom simulated profiles: Web, Database, Storage).
- **Incident Management**: Automatically triggers warning and critical alerts for high CPU, RAM, Disk, or Offline status. Ongoing breaches update in-place without generating hundreds of duplicate alert rows.
- **Auto-Resolution**: Once CPU or RAM utilization returns below threshold limits, active alerts automatically mark as resolved with an audit entry.
- **Dedicated Performance Analytics**: Target server dropdown selector, historical window switcher (15, 30, 60 samples), and live Chart.js trendlines.
- **Django Admin Interface**: Accessible at `http://127.0.0.1:8000/admin/` for inspecting database models.
- **Built-in Presentation Demo Helpers**: One-click buttons to simulate load spikes (95% CPU) and test alert generation in oral exams.

---

## 5. Running the Automated Test Suite

In the VS Code terminal, run:
```powershell
python manage.py test dashboard
```

All 7 test suites verify page rendering, REST APIs, server addition/deletion, status toggles, simulated spikes, alert lifecycles, settings modifications, and audit logs.
