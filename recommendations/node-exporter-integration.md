# Node Exporter via Prometheus — Implementation Plan

Use the **existing Prometheus MCP server** to query `node_exporter` infrastructure metrics (CPU, memory, disk, network, load) — no new MCP server or Docker container required.

## Why This Works

`node_exporter` metrics are already scraped into Prometheus. The agent already has Prometheus MCP tools. The only gaps are:
1. The agent's system prompt doesn't mention `node_exporter` metrics
2. There's no correlation between `postgres_exporter` and `node_exporter` instances on the same host

---

## Proposed Changes

### 1. Backend — System Prompt Update

#### [MODIFY] `backend/agent.py`

Extend `SYSTEM_PROMPT_TEMPLATE` to add node_exporter metric knowledge:

```diff
  You have two categories of tools:
  1. **Prometheus tools** — for querying PostgreSQL metrics (PromQL).
  2. **VictoriaLogs tools** — for querying PostgreSQL logs (LogsQL).
```

Add after the existing Prometheus metric list:

```
Key infrastructure metrics available via Prometheus (from node_exporter):
- CPU: node_cpu_seconds_total, node_load1, node_load5, node_load15
- Memory: node_memory_MemTotal_bytes, node_memory_MemAvailable_bytes,
  node_memory_MemFree_bytes, node_memory_Buffers_bytes, node_memory_Cached_bytes
- Disk: node_disk_read_bytes_total, node_disk_written_bytes_total,
  node_disk_io_time_seconds_total, node_filesystem_avail_bytes,
  node_filesystem_size_bytes
- Network: node_network_receive_bytes_total, node_network_transmit_bytes_total,
  node_network_receive_errs_total, node_network_transmit_errs_total
- System: node_boot_time_seconds, node_uname_info, node_time_seconds

When investigating infrastructure-level issues (CPU spikes, memory pressure,
disk full, I/O bottlenecks), use these node_exporter metrics via Prometheus tools.
Correlate infrastructure metrics with PostgreSQL metrics for holistic RCA.

Example PromQL queries for infrastructure:
- CPU usage: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
- Memory usage %: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
- Disk usage %: (1 - node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100
- Load average: node_load1, node_load5, node_load15
- Disk I/O rate: rate(node_disk_read_bytes_total[5m]), rate(node_disk_written_bytes_total[5m])
```

---

### 2. Backend — Instance Correlation Config (optional)

#### [NEW] `backend/server_mappings.yaml`

Map `postgres_exporter` instance to `node_exporter` instance on the same host, plus a friendly display name:

```yaml
servers:
  - display_name: "Production Primary"
    postgres_instance: "10.0.1.50:9187"
    node_instance: "10.0.1.50:9100"
  - display_name: "Production Replica"
    postgres_instance: "10.0.1.51:9187"
    node_instance: "10.0.1.51:9100"
```

If the postgres_exporter and node_exporter are on the same host (same IP, different ports), the agent can infer the mapping by matching the IP portion. The config file is only needed when the instances are on different IPs or need explicit names.

Add to system prompt:

```
Instance correlation for this environment:
{instance_mapping}
Use the node_exporter instance when querying infrastructure metrics,
and the postgres_exporter instance when querying database metrics.
```

---

### 3. Frontend — Suggestions Update

#### [MODIFY] `frontend/src/components/ChatWindow.tsx`

Add infrastructure-related suggestion prompts:

```diff
  const SUGGESTIONS = [
    "What's the overall health of my database?",
    "How many active connections are there right now?",
    "Is there any replication lag?",
    "Why is my database running slow?",
+   "What is the CPU and memory usage of the database server?",
+   "Is the disk running low on space?",
  ];
```

---

## What Does NOT Change

| Component | Status |
|-----------|--------|
| Docker Compose | ❌ No changes — no new container |
| `.env` | ❌ No changes — Prometheus URL already configured |
| `config.py` | ❌ No changes (unless adding server_mappings loader) |
| MCP server infra | ❌ No changes — reuses existing Prometheus MCP |
| Frontend API layer | ❌ No changes — same `/chat` endpoint |

---

## Verification Plan

1. **Verify node_exporter data exists in Prometheus**:
   ```
   curl "http://<prometheus>:9090/api/v1/query?query=node_load1"
   ```
2. **Start the app** and ask the agent:
   - *"What is the CPU utilization of the database server?"*
   - *"Is the server running low on memory?"*
   - *"Show me disk I/O over the last hour"*
3. **Verify the agent constructs correct PromQL** — should use `node_*` metrics via the existing Prometheus tools
4. **Correlation test**: *"Why is the database slow? Check both DB metrics and server resources."* — agent should query both `pg_*` and `node_*` metrics
