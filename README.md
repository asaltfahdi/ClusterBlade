# 🧠 ClusterBlade

**ClusterBlade** is a powerful yet lightweight **cluster management and monitoring dashboard** built with **Python + Gradio**.  
It allows you to **monitor, deploy, and secure** your ElasticSearch cluster nodes and virtual machines (VMs) through a clean, browser-based interface.

---

## ⚙️ Installing Dependencies

Before running **ClusterBlade**, make sure you have **Python 3.9 or higher** installed.

Follow these steps to install all required dependencies using the `pyproject.toml` file:

### 1️⃣ Create a virtual environment
It’s recommended to use a virtual environment to keep the project isolated.

#### 🪟 On Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```
#### 🐧 On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2️⃣ Install dependencies from pyproject.toml
Once your virtual environment is activated, install all dependencies with:
```bash
pip install .
```

---
### 🧩 Running on a Custom Port

By default, **ClusterBlade** runs on port **`7860`**.  
If you’d like to use a different port, simply specify it when launching the app using the `--port` flag:

```bash
python gradio_ui/app.py --port 8080
```
---
## 🚀 Features

### ✅ Real-Time Cluster Monitoring
- Dynamically loads node information from an `instances.yaml` file.  
- Detects both **VM status** (via SSH ping) and **ElasticSearch node status** (via HTTP check).  
- Each node card shows:
  - **🟢 / 🔴 Pulsing Dot** → ElasticSearch node health (green = ES running, red = ES down).  
  - **Card Outline Color** → VM connectivity (green = VM online, red = VM offline).  

### ✅ One-Click Cluster Deployment
- Automates the configuration and deployment of ElasticSearch nodes across multiple VMs.  
- Supports enabling/disabling SSL and HTTP options.  
- Provides progress tracking and detailed logs per node.  

### ✅ SSL Certificate Generator & Deployer
- Automatically generates secure SSL certificates for all cluster nodes.  
- Deploys certificates to remote nodes via SSH.  
- Supports password-protected or unencrypted certificates.  
- Re-generates certificates whenever cluster definitions change.  

### ✅ Clean Modern UI
- Built entirely with **Gradio Blocks** (no FastAPI needed).  
- Custom dark theme using `custom.css`.  
- Responsive design — node cards, dropdowns, and buttons align evenly in rows.  

### ✅ Self-Contained & Offline-Ready
- Runs standalone — no web server dependencies.  
- All assets (CSS, config, and YAML) load locally.  
- Ideal for on-premise cluster control.

---

## 🖥️ Status Indicators

| Element | Meaning | Description |
|----------|----------|-------------|
| **🟢 / 🔴 Dot** | **Elasticsearch Node Status** | Green = Node active, Red = Node down |
| **Card Outline** | **VM Connectivity** | Green = VM reachable, Red = VM offline |


## 📄 Example — `instances.yaml`

ClusterBlade uses a YAML file to know which VMs and ElasticSearch nodes exist in your environment.

```yaml
instances:
  - name: master-01
    ip: 10.0.0.11
    dns: es-master.local
  - name: data-01
    ip: 10.0.0.21
    dns: es-data.local
  - name: ingest-01
    ip: 10.0.0.31
    dns: es-ingest.local
  - name: cold-01
    ip: 10.0.0.41
    dns: es-cold.local

