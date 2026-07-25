# VIAIOS Enterprise 4.0 LTS

**Visual Intelligence AI Operating System** — 企业级视觉智能 AI 操作系统

## 系统架构

```
16 微服务 (13 Java + 3 Python) + 15 前端页面
├── API Gateway (8080) — Spring Cloud Gateway + JWT
├── Control Center (8081) — 用户/角色/租户管理
├── AI Kernel (8082) — 模型/资源/事件管理
├── Camera (8083) — 摄像头管理 + HLS 视频流
├── Analysis (8084) — AI 分析管线
├── Search (8085) — 向量检索引擎
├── Case (8086) — 案件管理 + 轨迹分析
├── Report (8087) — 报告生成
├── Alarm (8088) — 智能告警
├── Workflow (8089) — 工作流引擎
├── Agent Java (8091) — 8 内置 Agent
├── Capability Java (8092) — 12 AI 能力
├── Knowledge Java (8093) — 知识图谱
├── Agent Python (8191) — Planner/Memory/Search/Prompt
├── Capability Python (8192) — Model Manager/Benchmark
└── Knowledge Python (8193) — GraphRAG/Graph Query
```

## 快速开始

### 访问
```
URL: http://ry3.9gpu.com:18000
用户名: admin
密码: viaios-admin-2024
```

### 服务管理
```bash
# 检查全部服务
for p in 8080-8089 8091-8093 8191-8193; do
  curl -s -o /dev/null -w "$p: %{http_code}\n" http://localhost:$p/actuator/health
done

# 重启网关
systemctl restart viaios-gateway

# 重启 Python 服务
systemctl restart viaios-py-agent viaios-py-capability viaios-py-knowledge
```

## 15 个 AI 模块

| 模块 | API | 生产状态 |
|------|-----|---------|
| Planner | `POST /agents/plan` | ✅ |
| Memory | `POST /agents/memory/*` | ✅ SQLite持久化 |
| Model Manager | `POST /models/hot-swap` | ✅ |
| GraphRAG | `POST /knowledge/graphrag/query` | ✅ |
| Search | `POST /agents/search` | ✅ 缓存优化 |
| Prompt OS | `GET /prompts` | ✅ 持久化 |
| Security | `GET /security/roles` | ✅ 审计日志 |
| Policy | `GET /policies` | ✅ 持久化 |
| Runtime OS | Mesh 路由 | ✅ |
| Reasoning | `POST /reasoning/reason` | ✅ |
| Analytics | `GET /analytics/summary` | ✅ |
| Graph Query | `POST /graph/execute` | ✅ |
| Tenant | `GET /tenants` | ✅ 权限隔离 |
| GPU Scheduler | `GET /gpu/status` | ✅ |
| Notification | `GET /notifications` | ✅ 邮件模板 |

## 生产能力

- SQLite 持久化 (KV/Memory/Audit)
- 熔断器 (Circuit Breaker)
- LRU 缓存 (TTL + Hit Rate)
- 健康监控 (Prometheus 风格)
- 邮件通知 (SMTP 模板)
- 速率限制 + 重试

## 前端页面

Dashboard | Camera Detail | Search | Case Management | Alarm | Trajectory Map | Workflow Editor | Knowledge Graph | Reports | Admin

## 技术栈

**Backend**: Java 21 Spring Boot 3.2 + Python 3.8 FastAPI  
**Frontend**: React 18 TypeScript Vite Ant Design  
**AI**: ONNX Runtime + DeepSeek LLM  
**Infra**: PostgreSQL ClickHouse Milvus Kafka Redis Nginx systemd  

## 开发

```bash
# 前端开发
cd web/frontend && npm run dev

# 后端部署 (本地 → 服务器)
python C:/tmp/final_all.py

# 运行测试
npx playwright test tests/e2e/
```

---
**License**: Enterprise 4.0 LTS © VIAIOS
