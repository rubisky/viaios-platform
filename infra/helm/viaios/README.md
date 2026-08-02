# VIAIOS Helm Chart

## Quick Start
```bash
cd infra/helm/viaios
helm dependency update
helm install viaios . -f values.yaml
```

## Production Deploy
```bash
helm install viaios . -f values.yaml -f values-prod.yaml \
  --set global.imageTag=4.0.0 \
  --set aiKernel.env.CUDA_VISIBLE_DEVICES=0,1 \
  --set gateway.ingress.host=viaios.yourdomain.com
```

## Services (17 total)
| Service | Port | GPU | Autoscaling |
|---------|------|-----|-------------|
| gateway | 8080 | No | Yes (2-10) |
| controlCenter | 8081 | No | No |
| aiKernel | 8082 | Yes | No |
| videoAccess | 8083 | No | No |
| analysis | 8084 | No | Yes (2-8) |
| search | 8085 | No | No |
| caseService | 8086 | No | No |
| reportService | 8087 | No | No |
| alarmService | 8088 | No | No |
| workflowService | 8089 | No | No |
| agentService | 8191 | No | Yes (2-10) |
| capabilityService | 8192 | Yes | No |
| knowledgeService | 8193 | No | No |
| frontend | 3000 | No | No |

## Dependencies
- PostgreSQL (Bitnami)
- Kafka (Bitnami)  
- Redis (Bitnami)
- Milvus (Milvus Helm)
- MinIO (Bitnami)
- ClickHouse (Bitnami)

## Monitoring
```bash
# Enable monitoring stack
helm install viaios . -f values.yaml --set monitoring.enabled=true
```
Includes: Prometheus (100Gi), Grafana (pre-configured dashboards), Jaeger, Alertmanager
