# VIAIOS API Reference

Base URL: `http://<host>:18006`

## Authentication
```
POST /api/v1/auth/login
Body: {"username":"admin","password":"viaios-admin-2024"}
Response: {"accessToken":"...","refreshToken":"...","role":"ADMIN"}
```

## P0 — AI Kernel (8082)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/kernel/health` | All 11 managers status |
| GET | `/api/v1/kernel/topology` | 12-layer architecture |
| GET | `/api/v1/kernel/capabilities` | 16 capability domains |
| GET | `/api/v1/kernel/models` | 10 registered models |

## P0 — Runtime Mesh (8191)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/mesh/stats` | 8 endpoints, circuits, LB |
| GET | `/api/v1/mesh/endpoints` | All model endpoints |
| POST | `/api/v1/mesh/route?capability=X` | Route to best model |
| POST | `/api/v1/mesh/canary` | Setup canary deployment |

## P0 — Evidence Chain (8191)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/evidence/stats` | Registry statistics |
| GET | `/api/v1/evidence/chains` | List all chains |
| GET | `/api/v1/evidence/chain/:id` | Full chain audit |
| POST | `/api/v1/evidence/chain/:id/verify` | Verify integrity |

## P1 — GraphRAG (8191)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/graphrag/search` | Vector+Graph+LLM fusion |
| Body: `{"query":"...","mode":"full_rag"}` |

## P1 — Governance (8191)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/governance/policies` | 8 active policies |
| GET | `/api/v1/governance/stats` | Governance stats |
| GET | `/api/v1/governance/audit` | Audit log entries |

## P2 — Triton (8191)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/triton/health` | Triton server status |
| GET | `/api/v1/triton/models` | Registered models |

## P2 — GB28181 (8191)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/cameras/gb28181/stats` | Server statistics |
| GET | `/api/v1/cameras/gb28181/devices` | Registered cameras |
| POST | `/api/v1/cameras/gb28181/register` | Register camera |
| POST | `/api/v1/cameras/gb28181/:id/preview` | Start live stream |

## P2 — Video Service (8094)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/video/stats` | Stream statistics |
| GET | `/api/v1/video/streams` | Active streams |
| POST | `/api/v1/video/streams` | Add RTSP stream |
| POST | `/api/v1/video/rtsp/proxy` | RTSP→HLS proxy |

## Core Services
| Path | Port |
|------|------|
| `/api/v1/cameras` | 8083 |
| `/api/v1/cases` | 8086 |
| `/api/v1/search` | 8085 |
| `/api/v1/alarms` | 8088 |
| `/api/v1/reports` | 8087 |
| `/api/v1/analysis` | 8084 |
| `/api/v1/agents` | 8191 |
| `/api/system/services` | 8191 |
