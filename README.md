# VIAIOS Monorepo

## 快速开始

### 环境要求
- JDK 21 (Eclipse Temurin)
- Python 3.11+
- Node.js 20 LTS
- Docker 24+
- Gradle 8.5+ (wrapper included)

### 一键启动
```bash
# macOS/Linux
./scripts/setup.sh

# Windows
scripts\setup.bat
```

### 服务列表

| 服务 | 端口 | 技术栈 | 说明 |
|------|------|--------|------|
| api-gateway | 8080 | Spring Cloud Gateway | API 网关 |
| control-center | 8081 | Spring Boot | 控制中心 |
| ai-kernel | 8082 | Spring Boot | AI 内核 |
| video-access | 8083 | Spring Boot | 视频接入 |
| analysis | 8084 | Spring Boot | AI 分析 |
| search | 8085 | Spring Boot | 目标检索 |
| case-service | 8086 | Spring Boot | 案件管理 |
| report-service | 8087 | Spring Boot | 报告生成 |
| alarm-service | 8088 | Spring Boot | 智能布控 |
| workflow-service | 8089 | Spring Boot | 流程编排 |
| agent-service | 8091 | Python/FastAPI | Agent 运行时 |
| capability-service | 8092 | Python/FastAPI | 能力市场 |
| knowledge-service | 8093 | Python/FastAPI | 知识图谱 |
| frontend | 3000 | React/TypeScript | Web 前端 |

### 架构
详见 `../viaios/docs/` 下的详细设计文档。
