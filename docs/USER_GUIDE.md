# VIAIOS Enterprise 4.0 — User Guide

## Quick Start
1. Open browser: `http://<host>:18006`
2. Login: `admin` / `viaios-admin-2024`
3. Dashboard shows system overview

## Navigation

| Menu | Description |
|------|-------------|
| 视频侦查 | Dashboard — system overview, charts, service status |
| 目标检索 | AI-powered target search (image/text/attribute) |
| 摄像头 | Camera list + live view |
| 案件管理 | Case management with evidence |
| 智能研判 | Alarm Center — real-time surveillance alerts NEW |
| 轨迹回放 | 3D trajectory replay on Cesium globe |
| 工作流 | Visual workflow editor |
| 报告中心 | AI-generated reports |
| 知识图谱 | Knowledge graph visualization |
| 系统管理 | Admin panel |
| 模型管理 | AI model lifecycle dashboard NEW |
| 审计日志 | Governance audit + evidence chains NEW |
| 系统诊断 | Real-time 18-service health monitor NEW |
| 设置向导 | System configuration wizard NEW |

## Key Features

### AI Model Management (/models)
- View all registered AI models (YOLOv8, ResNet, ArcFace, CLIP, etc.)
- Deploy/pause/retire models
- Model metrics (latency, throughput, GPU usage)

### Alarm Center (/surveillance)
- Real-time alarm monitoring
- Surveillance rules: intrusion, vehicle, offline, crowd
- Acknowledge/Resolve alarms
- Auto-escalation (3 levels)

### Evidence Chain
- Blockchain-style hash chain for AI audit
- Full traceability: video → algorithm → model → inference → conclusion
- Chain integrity verification

### System Diagnostics (/diagnostics)
- 18-service real-time health monitoring
- 10-second auto-refresh
- Kernel manager status

## API Quick Reference
```
POST /api/v1/auth/login       — Authentication
GET  /api/v1/kernel/health     — AI Kernel status
GET  /api/v1/cameras           — Camera list
POST /api/v1/graphrag/search   — AI knowledge search
GET  /api/v1/governance/stats  — Security audit
```

## Troubleshooting
- Login fails: check `systemctl status viaios-gateway`
- Page 404: check `nginx -t && systemctl restart nginx`
- Service down: `for p in 8080-8089 8094 8191-8193; do curl -s localhost:$p/health; done`
