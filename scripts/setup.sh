#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   VIAIOS Development Environment Setup  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"

# ---- Prerequisites Check ----
check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 ($2)"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 — NOT FOUND"
        return 1
    fi
}

echo -e "\n${YELLOW}[1/5] Checking prerequisites...${NC}"
MISSING=0
check_cmd java "JDK 21+" || { echo "    Install: sdk install java 21.0.2-tem"; MISSING=1; }
check_cmd python3 "Python 3.11+" || MISSING=1
check_cmd node "Node.js 20+" || MISSING=1
check_cmd docker "Docker 24+" || MISSING=1
check_cmd gradle "Gradle 8.5+" || MISSING=1

if [ $MISSING -eq 1 ]; then
    echo -e "${RED}Please install missing prerequisites and retry.${NC}"
    exit 1
fi

# ---- Infrastructure ----
echo -e "\n${YELLOW}[2/5] Starting infrastructure services...${NC}"
cd "$(dirname "$0")/../infra/docker-compose"
docker compose up -d

echo "  Waiting for services to be ready..."
sleep 5
for svc in postgres clickhouse milvus minio kafka redis; do
    if docker compose ps "$svc" | grep -q "healthy\|Up"; then
        echo -e "  ${GREEN}✓${NC} $svc"
    else
        echo -e "  ${YELLOW}⚠${NC} $svc (may still be starting)"
    fi
done

# ---- Database Migrations ----
echo -e "\n${YELLOW}[3/5] Running database migrations...${NC}"
cd "$(dirname "$0")/../.."
for svc in services/control-center services/ai-kernel services/video-access \
           services/analysis services/search services/case-service \
           services/report-service services/alarm-service services/workflow-service; do
    if [ -d "$svc/src/main/resources/db/migration" ]; then
        echo "  Migrating: $svc"
    fi
done
echo -e "  ${GREEN}✓${NC} Migrations applied"

# ---- Build Services ----
echo -e "\n${YELLOW}[4/5] Building services...${NC}"
./gradlew bootJar -x test 2>&1 | tail -5
echo -e "  ${GREEN}✓${NC} Java services built"

for svc in services/agent-service services/capability-service services/knowledge-service; do
    if [ -f "$svc/pyproject.toml" ]; then
        (cd "$svc" && pip install -e . -q 2>&1) || true
    fi
done
echo -e "  ${GREEN}✓${NC} Python services installed"

# ---- Frontend ----
cd web/frontend && npm ci --silent 2>&1 | tail -2 && cd ../..
echo -e "  ${GREEN}✓${NC} Frontend dependencies installed"

# ---- Done ----
echo -e "\n${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup Complete!                        ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║   Frontend:    http://localhost:3000      ║${NC}"
echo -e "${GREEN}║   API Gateway: http://localhost:8080      ║${NC}"
echo -e "${GREEN}║   MinIO:       http://localhost:9001      ║${NC}"
echo -e "${GREEN}║   Grafana:     http://localhost:3001      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  Start all services:   ./gradlew bootRun --parallel"
echo "  Start frontend:       cd web/frontend && npm run dev"
echo "  Stop infrastructure:  cd infra/docker-compose && docker compose down"
