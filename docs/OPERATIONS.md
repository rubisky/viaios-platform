# VIAIOS Enterprise 4.0 LTS — Operations Guide

## Server Access
```
Host: ry3.9gpu.com
SSH:  ssh root@<host> -p <port>
Web:  http://<host>:18006
```

## Service Map

| Port | Service | Lang | Health Check |
|------|---------|------|-------------|
| 8880 | Nginx (→18006) | — | `curl localhost:8880/` |
| 8080 | Gateway | Java | `/actuator/health` |
| 8081 | Control Center | Java | `/actuator/health` |
| 8082 | AI Kernel | Java | `/api/v1/kernel/health` |
| 8083 | Cameras | Java | `/actuator/health` |
| 8084 | Analysis | Java | `/actuator/health` |
| 8085 | Search | Java | `/actuator/health` |
| 8086 | Cases | Java | `/actuator/health` |
| 8087 | Reports | Java | `/actuator/health` |
| 8088 | Alarms | Java | `/actuator/health` |
| 8089 | Workflow | Java | `/actuator/health` |
| 8091 | Agent (Java) | Java | `/actuator/health` |
| 8092 | Capability (Java) | Java | `/actuator/health` |
| 8093 | Knowledge (Java) | Java | `/actuator/health` |
| 8094 | Video Service | Python | `/health` |
| 8191 | Agent (Python) | Python | `/health` |
| 8192 | Capability (Python) | Python | `/health` |
| 8193 | Knowledge (Python) | Python | `/health` |

## Health Check (All Services)
```bash
for p in 8080-8089 8091-8093 8094 8191-8193; do
  s=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$p/actuator/health 2>/dev/null)
  [ -z "$s" ] && s=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$p/health 2>/dev/null)
  echo "$p: $s"
done
```

## Restart Procedures

### Nginx
```bash
nginx -t && systemctl restart nginx
```

### Python Services (systemd)
```bash
systemctl restart viaios-py-agent viaios-py-capability viaios-py-knowledge viaios-video
```

### Java Services (manual)
```bash
# AI Kernel
pkill -f ai-kernel; sleep 2
nohup java -jar /opt/viaios/services/ai-kernel/build/libs/ai-kernel.jar --server.port=8082 > /var/log/viaios-ai-kernel.log 2>&1 &

# Gateway
nohup java -jar /opt/viaios/gateway/api-gateway/build/libs/api-gateway.jar --viaios.jwt.secret=<your-jwt-secret> > /tmp/gw.log 2>&1 &
```

### Rebuild Gateway
```bash
cd /opt/viaios
./gradlew :gateway:api-gateway:bootJar -x test --no-daemon
systemctl restart viaios-gateway  # or use nohup above
```

### Rebuild AI Kernel
```bash
cd /opt/viaios
./gradlew :services:ai-kernel:bootJar -x test --no-daemon
pkill -f ai-kernel; sleep 2
nohup java -jar /opt/viaios/services/ai-kernel/build/libs/ai-kernel.jar --server.port=8082 > /var/log/viaios-ai-kernel.log 2>&1 &
```

## Logs
```bash
# Python services
journalctl -u viaios-py-agent -f
journalctl -u viaios-video -f

# Java services
tail -f /var/log/viaios-ai-kernel.log
tail -f /tmp/gw.log
```

## API Endpoints (P0+P1+P2)
```
P0: /api/v1/kernel/*        — AI Kernel (health/topology/capabilities/models)
P0: /api/v1/mesh/*          — Runtime Mesh (stats/endpoints/route/canary)
P0: /api/v1/evidence/*      — Evidence Chain (stats/chains/verify)
P0: /api/v1/capabilities/*  — AI Pipelines (list/run)
P0: /api/v1/video/*         — Video Pipeline (process/status)
P1: /api/v1/graphrag/*      — GraphRAG Fusion
P1: /api/v1/workflow/*      — Workflow DSL
P1: /api/v1/evaluator/*     — Agent Evaluator
P1: /api/v1/governance/*    — Governance (policies/stats/audit)
P2: /api/v1/triton/*        — Triton Inference Server
P2: /api/v1/cameras/gb28181/* — GB28181 Camera Protocol
```

## Frontend Deploy
```bash
# From local machine:
cd d:/2026viaiso/code/viaios-monorepo/web/frontend
npm run build
# Upload dist/ to /opt/viaios/frontend/dist/ on server
# Then: nginx -s reload
```

## Troubleshooting

### Login 500
1. Check Control Center: `curl localhost:8081/actuator/health`
2. Check nginx auth route: `grep auth /etc/nginx/sites-available/viaios`
3. Test direct: `curl -X POST localhost:8081/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"viaios-admin-2024"}'`

### Gateway Crash Loop
1. Stop systemd: `systemctl stop viaios-gateway && systemctl disable viaios-gateway`
2. Start manually: `nohup java -jar /opt/viaios/gateway/api-gateway/build/libs/api-gateway.jar --viaios.jwt.secret=... > /tmp/gw.log 2>&1 &`
3. Check log: `tail -20 /tmp/gw.log`

### Nginx Config Location
`/etc/nginx/sites-available/viaios`
