# PatchIO Elasticsearch Setup Guide (Windows, macOS, Linux)

This document explains how developers can install and configure Elasticsearch locally for PatchIO across Windows, macOS, and Linux. It includes security notes for Elasticsearch 8.x, verification steps, and how to connect PatchIO to your local ES node.

Important notes

- Use Elasticsearch 8.x. It ships with a bundled JDK; a separate Java install is not required.
- Security (TLS + authentication) is enabled by default in ES 8.x. You will need the elastic user password generated on first start, or reset it.
- PatchIO will create the index with the correct mappings automatically on first run if credentials are valid.

Contents

- Quick Start (TL;DR)
- OS-specific installation
  - Ubuntu/Debian (apt)
  - RHEL/CentOS/Fedora (dnf/yum)
  - Generic Linux (tar.gz)
  - macOS (Homebrew or tar.gz)
  - Windows (MSI or ZIP)
- Configuration for local development
- Security and credentials in ES 8.x
- Verify your installation
- Connect PatchIO to Elasticsearch
- Optional: Manual index creation/mapping
- Troubleshooting
- Uninstall/Cleanup

---

Quick Start (TL;DR)

1. Install Elasticsearch 8.x for your OS (see below).
2. Start Elasticsearch.
3. Get or reset the elastic user password (ES 8.x).
4. Verify: curl -k -u elastic:YOUR_PASSWORD https://localhost:9200
5. Configure PatchIO settings:
   - ELASTICSEARCH_ENABLED = True
   - ELASTICSEARCH_HOSTS = ["https://localhost:9200"]
   - ELASTICSEARCH_USERNAME = "elastic"
   - ELASTICSEARCH_PASSWORD = "YOUR_PASSWORD"
   - ELASTICSEARCH_SSL_VERIFY = False (for local self-signed)
   - ELASTICSEARCH_INDEX = "patchio_files"
6. Run PatchIO. The app will ensure the index exists and start syncing.

---

Install on Ubuntu/Debian (apt)

1. Import the Elastic GPG key:
   curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elastic.gpg

2. Add the 8.x APT repository:
   echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

3. Update and install:
   sudo apt update
   sudo apt install elasticsearch

4. Enable service at boot and start:
   sudo systemctl enable elasticsearch
   sudo systemctl start elasticsearch

5. Check status:
   sudo systemctl status elasticsearch

Install on RHEL/CentOS/Fedora (dnf/yum)

1. Create repo file /etc/yum.repos.d/elasticsearch.repo with:
   [elasticsearch-8.x]
   name=Elasticsearch repository for 8.x packages
   baseurl=https://artifacts.elastic.co/packages/8.x/yum
   gpgcheck=1
   gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
   enabled=1
   autorefresh=1
   type=rpm-md

2. Install:
   sudo dnf install elasticsearch

   # or: sudo yum install elasticsearch

3. Enable and start:
   sudo systemctl enable elasticsearch
   sudo systemctl start elasticsearch

Generic Linux (tar.gz)

1. Download the Linux x86_64 tarball from:
   https://www.elastic.co/downloads/elasticsearch

2. Extract and run:
   tar -xzf elasticsearch-8.x.x-linux-x86_64.tar.gz
   cd elasticsearch-8.x.x
   ./bin/elasticsearch

3. Logs will show the generated elastic password on first run.

Install on macOS (Homebrew)
Option A: Homebrew (recommended)

1. Tap Elastic’s Homebrew repo:
   brew tap elastic/tap

2. Install Elasticsearch:
   brew install elastic/tap/elasticsearch-full

3. Start as a service:
   brew services start elastic/tap/elasticsearch-full

4. Stop if needed:
   brew services stop elastic/tap/elasticsearch-full

Option B: tar.gz

- Download macOS tarball, extract, and run ./bin/elasticsearch (similar to Linux tar.gz steps).

Install on Windows (MSI or ZIP)
Option A: MSI Installer (easiest)

1. Download the Windows MSI from:
   https://www.elastic.co/downloads/elasticsearch
2. Run the installer. It can install Elasticsearch as a Windows service.
3. Start the service from Services MMC or:
   sc start elasticsearch

Option B: ZIP (manual)

1. Download elasticsearch-8.x.x-windows-x86_64.zip
2. Extract, then open an elevated PowerShell in the folder.
3. Start in console:
   .\bin\elasticsearch.bat
   or install service:
   .\bin\elasticsearch-service.bat install
   .\bin\elasticsearch-service.bat start

---

Configuration for local development
Defaults are often enough for local use. If you need to edit configuration:

- Linux packages: /etc/elasticsearch/elasticsearch.yml
- Homebrew macOS: /opt/homebrew/etc/elasticsearch/elasticsearch.yml (Apple Silicon) or /usr/local/etc/elasticsearch/elasticsearch.yml (Intel)
- tar/zip: elasticsearch-8.x.x/config/elasticsearch.yml
- Windows MSI/ZIP: config/elasticsearch.yml in the install dir

Recommended settings for local dev:

- Leave security on (default in 8.x). PatchIO can use username/password.
- If you must bind to all interfaces (not recommended), set:
  network.host: 0.0.0.0
  discovery.type: single-node
  Then restart service. Be aware of security risks if your machine is on a network.

Memory/Heap (optional):

- Edit jvm.options to set -Xms and -Xmx. Defaults are often fine for local dev.

Linux only: required kernel setting for large clusters (not usually needed for a single-node dev):
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

---

Security and credentials in Elasticsearch 8.x

- Security is enabled by default: HTTPS, user auth, and built-in users.
- On first start, ES prints a generated elastic user password to the logs/console.
  - Debian/Ubuntu: /var/log/elasticsearch/elasticsearch.log
  - Homebrew macOS: /opt/homebrew/var/log/elasticsearch/elasticsearch.log or /usr/local/var/log/...
  - tar/zip: ./logs/elasticsearch.log
  - Windows service: logs directory under install path; also Windows Event Viewer

Reset the elastic password if needed:

- Linux/macOS:
  sudo /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
  # or in tar dir:
  ./bin/elasticsearch-reset-password -u elastic -i
- Windows:
  .\bin\elasticsearch-reset-password.bat -u elastic -i

Self-signed TLS:

- ES runs HTTPS with a self-signed cert by default. For local dev you can either:
  - Set ELASTICSEARCH_SSL_VERIFY=False in PatchIO settings, or
  - Import the cert into your system trust store and keep verification on.

Disable security (not recommended):

- You can set xpack.security.enabled: false in elasticsearch.yml and restart, but this is discouraged. Prefer using credentials.

---

Verify your installation
Check ES is running and reachable:

- If security enabled (default):
  curl -k -u elastic:YOUR_PASSWORD https://localhost:9200
- If security disabled:
  curl http://localhost:9200

Expected response: JSON with cluster_name and version number.

Quick API checks:

- List indices:
  curl -k -u elastic:YOUR_PASSWORD https://localhost:9200/\_cat/indices?v
- Create a test doc:
  curl -k -u elastic:YOUR_PASSWORD -H 'Content-Type: application/json' \
   -X POST 'https://localhost:9200/test_index/\_doc/1' \
   -d '{"hello":"world"}'
- Search:
  curl -k -u elastic:YOUR_PASSWORD 'https://localhost:9200/test_index/\_search?q=hello:world'

---

Connect PatchIO to Elasticsearch
PatchIO uses these settings in settings/core_settings.py:

- ELASTICSEARCH_ENABLED = True
- ELASTICSEARCH_HOSTS = ["https://localhost:9200"] # or your host(s)
- ELASTICSEARCH_USERNAME = "elastic"
- ELASTICSEARCH_PASSWORD = "YOUR_PASSWORD"
- ELASTICSEARCH_SSL_VERIFY = False # True if you trust the cert
- ELASTICSEARCH_INDEX = "patchio_files"

How it works:

- PatchIO initializes an ES client and pings the cluster.
- On success, it ensures the index exists with mappings optimized for PatchIO (autocomplete, full-text, keywords).
- Real-time file changes and batch syncs are pushed to ES from SQLite (SQLite is the source of truth).

If you don’t want to edit the app’s settings file, you can export equivalent environment variables and have your settings loader read them (if supported in your project). Otherwise, edit settings/core_settings.py directly.

---

Optional: Manual index creation (if you want to pre-create)
PatchIO creates the index automatically. If you want to create it manually in Kibana Dev Tools or via curl:

PUT patchio_files
{
"settings": {
"number_of_shards": 1,
"number_of_replicas": 0,
"analysis": {
"filter": {
"edge_ngram_filter": { "type": "edge_ngram", "min_gram": 1, "max_gram": 20 }
},
"analyzer": {
"autocomplete_analyzer": {
"tokenizer": "standard",
"filter": ["lowercase", "edge_ngram_filter"]
},
"autocomplete_search_analyzer": {
"tokenizer": "standard",
"filter": ["lowercase"]
}
}
}
},
"mappings": {
"properties": {
"path": { "type": "keyword" },
"name": {
"type": "text",
"analyzer": "standard",
"fields": {
"raw": { "type": "keyword" },
"ac": {
"type": "text",
"analyzer": "autocomplete_analyzer",
"search_analyzer": "autocomplete_search_analyzer"
}
}
},
"vendor": {
"type": "text",
"fields": {
"raw": { "type": "keyword" },
"ac": {
"type": "text",
"analyzer": "autocomplete_analyzer",
"search_analyzer": "autocomplete_search_analyzer"
}
}
},
"library": {
"type": "text",
"fields": {
"raw": { "type": "keyword" },
"ac": {
"type": "text",
"analyzer": "autocomplete_analyzer",
"search_analyzer": "autocomplete_search_analyzer"
}
}
},
"instrument": { "type": "keyword" },
"genre": { "type": "keyword" },
"tags": { "type": "keyword" },
"file_type": { "type": "keyword" },
"extension": { "type": "keyword" },
"parent_folder": { "type": "keyword" },
"bpm": { "type": "keyword" },
"key": { "type": "keyword" },
"modified_time": { "type": "date", "format": "epoch_second" },
"created_at": { "type": "date", "format": "epoch_second" },
"fulltext": { "type": "text", "analyzer": "standard" }
}
}
}

---

Troubleshooting

- Service won’t start

  - Linux: check sudo systemctl status elasticsearch and logs in /var/log/elasticsearch/
  - macOS (Homebrew): brew services list; logs in /usr/local/var/log/elasticsearch or /opt/homebrew/var/log/elasticsearch
  - Windows: check Services and Event Viewer; logs under the install directory’s logs folder.

- Authentication failures (401)

  - Ensure you’re using the elastic user and the correct password.
  - Reset password if needed (see Security section).

- SSL certificate or “certificate verify failed”

  - Use ELASTICSEARCH_SSL_VERIFY=False for local dev with self-signed certs, or add the cert to your trust store and keep verify=True.

- Port already in use

  - Default HTTP port is 9200; change http.port in elasticsearch.yml or stop the conflicting service.

- Index not created automatically

  - Ensure PatchIO logs show “Elasticsearch client created” and “ensure_index” running.
  - Check credentials; the app can’t create the index if auth fails.

- “vm.max_map_count” on Linux

  - For larger datasets or Docker-based setups, set:
    sudo sysctl -w vm.max_map_count=262144

- Slow performance
  - For local dev, set number_of_replicas: 0.
  - Ensure you’re not indexing to a remote, slow node.
  - Check heap settings in jvm.options if your machine is memory-constrained.

---

Uninstall / Cleanup

- Ubuntu/Debian:
  sudo systemctl stop elasticsearch
  sudo apt remove --purge elasticsearch
  sudo rm -rf /var/lib/elasticsearch /var/log/elasticsearch /etc/elasticsearch

- RHEL/CentOS/Fedora:
  sudo systemctl stop elasticsearch
  sudo dnf remove elasticsearch
  sudo rm -rf /var/lib/elasticsearch /var/log/elasticsearch /etc/elasticsearch

- macOS (Homebrew):
  brew services stop elastic/tap/elasticsearch-full
  brew uninstall elastic/tap/elasticsearch-full
  rm -rf /usr/local/var/lib/elasticsearch /usr/local/var/log/elasticsearch

  # or /opt/homebrew/var/... on Apple Silicon

- Windows:
  If installed as a service:
  .\bin\elasticsearch-service.bat stop
  .\bin\elasticsearch-service.bat remove
  Then delete the installation directory.

---

FAQ

- Do I need Java installed separately?

  - No. Elasticsearch 8.x bundles a JDK.

- Can I run without security locally?

  - Yes (set xpack.security.enabled: false), but it’s discouraged. Prefer using the default security with the elastic user and self-signed TLS.

- Does PatchIO need me to create the index manually?

  - No. PatchIO creates the index and mappings automatically if it has permissions.

- What index name should I use?

  - Default is patchio_files (configure via ELASTICSEARCH_INDEX).

- How do I check that PatchIO is talking to ES?
  - Look for PatchIO logs: “Elasticsearch client created”, “ping ok”, “Created ES index: patchio_files” or “ES bulk indexed …”. You can also check \_cat/indices.

That’s it. With the above steps, developers on Windows, macOS, and Linux can set up a secure local Elasticsearch 8.x and connect PatchIO for real-time and batch indexing.
