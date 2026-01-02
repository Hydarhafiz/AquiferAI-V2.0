# Cloud-Native Architecture Proposal
## AquiferAI v2.0 Infrastructure Design

**Document Version:** 1.0
**Author:** Solutions Architecture Team
**Status:** PROPOSED
**Last Updated:** 2026-01-01

---

## Executive Summary

This document outlines the migration strategy from a local Dockerized deployment to a production-grade cloud-native architecture on AWS. The proposal addresses the scalability limitations identified in V1 UAT testing and establishes a foundation for enterprise adoption.

---

## 1. Current State Analysis

### 1.1 V1 Architecture Limitations

| Component | Current Implementation | Limitation |
|-----------|----------------------|------------|
| LLM Inference | Ollama (local, RTX 3080) | Single-node, no failover, 10GB VRAM constraint |
| Graph Database | Neo4j Community (Docker) | No clustering, manual backups, limited to local storage |
| API Layer | FastAPI (single container) | No horizontal scaling, single point of failure |
| Frontend | React/Vite (local dev server) | No CDN, no SSL termination |
| Chat History | PostgreSQL (Docker) | No replication, local persistence only |

### 1.2 V1 Performance Baseline (from UAT)

- Average query response time: ~8-15 seconds (LLM inference bound)
- Concurrent user capacity: 1-3 users
- Cypher query generation accuracy: ~85% (improvement needed)
- Maximum dataset retrieval: 3,677 records (Amazon + Parnaiba comparison)

---

## 2. Target Architecture

### 2.1 Architecture Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET / USERS                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AWS CLOUDFRONT (CDN)                                     │
│                    - SSL Termination                                             │
│                    - Static Asset Caching                                        │
│                    - Edge Locations (Global)                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────────┐
│      S3 BUCKET (Frontend)         │   │     APPLICATION LOAD BALANCER         │
│  - React Build Artifacts          │   │  - Health Checks                      │
│  - Static Assets                  │   │  - Path-Based Routing                 │
│  - Versioned Deployments          │   │  - WebSocket Support                  │
└───────────────────────────────────┘   └───────────────────────────────────────┘
                                                            │
                            ┌───────────────────────────────┼───────────────────┐
                            │                               │                   │
                            ▼                               ▼                   ▼
              ┌─────────────────────────┐   ┌─────────────────────────┐   ┌──────────┐
              │   ECS FARGATE CLUSTER   │   │   ECS FARGATE CLUSTER   │   │  FUTURE  │
              │   (API Service)         │   │   (Agent Orchestrator)  │   │  SCALE   │
              │                         │   │                         │   │          │
              │ ┌─────────────────────┐ │   │ ┌─────────────────────┐ │   │          │
              │ │  FastAPI Container  │ │   │ │  LangGraph Agents   │ │   │          │
              │ │  - /api/*           │ │   │ │  - Planner          │ │   │          │
              │ │  - /chat/*          │ │   │ │  - Cypher Specialist│ │   │          │
              │ │  - Auto-scaling     │ │   │ │  - Validator        │ │   │          │
              │ └─────────────────────┘ │   │ │  - Analyst          │ │   │          │
              │                         │   │ └─────────────────────┘ │   │          │
              └─────────────────────────┘   └─────────────────────────┘   └──────────┘
                            │                               │
                            └───────────────┬───────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        │                                   │                                   │
        ▼                                   ▼                                   ▼
┌───────────────────────┐   ┌───────────────────────────────┐   ┌───────────────────────┐
│   NEO4J AURADB        │   │     AMAZON BEDROCK            │   │   AMAZON RDS          │
│   (Managed Graph DB)  │   │     (LLM Inference)           │   │   (PostgreSQL)        │
│                       │   │                               │   │                       │
│ - Enterprise Tier     │   │ ┌───────────────────────────┐ │   │ - Multi-AZ            │
│ - Auto-backups        │   │ │ Claude 3.5 Sonnet         │ │   │ - Read Replicas       │
│ - 99.95% SLA          │   │ │ (Primary - Analysis)      │ │   │ - Automated Backups   │
│ - Vector Search       │   │ └───────────────────────────┘ │   │ - Chat History        │
│ - 104,390 nodes       │   │ ┌───────────────────────────┐ │   │ - User Sessions       │
│                       │   │ │ Claude 3.5 Haiku          │ │   │ - Saved Analyses      │
└───────────────────────┘   │ │ (Cypher Generation)       │ │   └───────────────────────┘
                            │ └───────────────────────────┘ │
                            └───────────────────────────────┘
                                            │
                            ┌───────────────┴───────────────┐
                            │                               │
                            ▼                               ▼
              ┌─────────────────────────┐   ┌─────────────────────────┐
              │   AMAZON ELASTICACHE    │   │   AWS SECRETS MANAGER   │
              │   (Redis)               │   │                         │
              │                         │   │ - API Keys              │
              │ - Session Caching       │   │ - DB Credentials        │
              │ - Query Result Cache    │   │ - LLM Tokens            │
              │ - Rate Limiting         │   │                         │
              └─────────────────────────┘   └─────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           OBSERVABILITY LAYER                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐               │
│  │ CloudWatch Logs  │  │ CloudWatch       │  │ AWS X-Ray        │               │
│  │ - API Logs       │  │ Metrics          │  │ - Distributed    │               │
│  │ - LLM Traces     │  │ - Latency        │  │   Tracing        │               │
│  │ - Error Tracking │  │ - Throughput     │  │ - LLM Call Trace │               │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Migration Strategy

### 3.1 LLM Inference: Ollama → Amazon Bedrock

**Rationale:** Eliminates GPU management overhead, provides enterprise SLAs, and enables access to frontier models.

| Aspect | V1 (Ollama) | V2 (Bedrock) |
|--------|-------------|--------------|
| Cypher Generation | qwen2.5-coder:7b | Claude 3.5 Haiku (cost-optimized) |
| Analysis/Synthesis | llama3:8b | Claude 3.5 Sonnet (quality-optimized) |
| Availability | Single node | Multi-region, 99.9% SLA |
| Scaling | Manual GPU allocation | Auto-scaling on demand |
| Cost Model | Fixed (hardware) | Pay-per-token |

**Migration Steps:**
1. Abstract LLM calls behind `LLMProvider` interface
2. Implement `BedrockProvider` alongside existing `OllamaProvider`
3. Update prompts for Claude's instruction format
4. A/B test Cypher accuracy (target: 95%+ valid queries)
5. Gradual traffic shift with feature flags

**Bedrock Configuration:**
```python
# config/llm_config.py
BEDROCK_CONFIG = {
    "cypher_model": {
        "model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "max_tokens": 2048,
        "temperature": 0.1,  # Low temp for deterministic Cypher
    },
    "analysis_model": {
        "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "max_tokens": 4096,
        "temperature": 0.3,
    }
}
```

### 3.2 Graph Database: Neo4j Docker → Neo4j AuraDB

**Rationale:** Managed service eliminates operational burden, provides enterprise features.

| Feature | V1 (Community) | V2 (AuraDB Professional) |
|---------|---------------|-------------------------|
| High Availability | None | Multi-AZ automatic failover |
| Backups | Manual scripts | Continuous + point-in-time recovery |
| Scaling | Vertical only | Vertical + read replicas |
| Vector Search | Not available | Native vector indexes |
| Monitoring | Manual | Built-in + CloudWatch integration |

**Data Migration Plan:**
```bash
# Phase 1: Export from local Neo4j
neo4j-admin database dump --database=neo4j --to-path=/backup/aquifer-v1.dump

# Phase 2: Import to AuraDB (via Aura Console or CLI)
aura-cli db import --instance-id=<AURA_ID> --source=/backup/aquifer-v1.dump

# Phase 3: Verify data integrity
MATCH (a:Aquifer) RETURN count(a) AS total_aquifers
// Expected: 104,390

# Phase 4: Create full-text indexes (required for basin/country search)
CREATE FULLTEXT INDEX basinSearch FOR (b:Basin) ON EACH [b.Basin_name]
CREATE FULLTEXT INDEX countrySearch FOR (c:Country) ON EACH [c.Country_name]
```

**Connection String Update:**
```python
# V1
NEO4J_URI = "bolt://neo4j:7687"

# V2
NEO4J_URI = "neo4j+s://<AURA_INSTANCE_ID>.databases.neo4j.io"
```

### 3.3 API Layer: Single Container → ECS Fargate

**Service Configuration:**
```yaml
# ecs-task-definition.yaml
family: aquifer-api
networkMode: awsvpc
requiresCompatibilities:
  - FARGATE
cpu: "1024"
memory: "2048"
containerDefinitions:
  - name: fastapi-app
    image: <ECR_REPO>/aquifer-api:latest
    portMappings:
      - containerPort: 8000
        protocol: tcp
    environment:
      - name: NEO4J_URI
        valueFrom: arn:aws:secretsmanager:...
      - name: DATABASE_URL
        valueFrom: arn:aws:secretsmanager:...
    healthCheck:
      command: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 30
      timeout: 5
      retries: 3
```

**Auto-Scaling Policy:**
```yaml
# Target: 70% CPU utilization
ScalingPolicy:
  TargetTrackingScaling:
    TargetValue: 70.0
    PredefinedMetricType: ECSServiceAverageCPUUtilization
  MinCapacity: 2
  MaxCapacity: 10
```

### 3.4 Frontend: Local Dev → S3 + CloudFront

**Deployment Pipeline:**
```yaml
# .github/workflows/frontend-deploy.yml
name: Deploy Frontend
on:
  push:
    branches: [main]
    paths: ['client/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
        working-directory: ./client
      - run: npm run build
        working-directory: ./client
        env:
          VITE_API_URL: ${{ secrets.API_URL }}
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
      - run: |
          aws s3 sync ./client/dist s3://${{ secrets.S3_BUCKET }} --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DIST_ID }} --paths "/*"
```

---

## 4. Network Architecture

### 4.1 VPC Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        VPC: 10.0.0.0/16                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PUBLIC SUBNETS (10.0.1.0/24, 10.0.2.0/24)  │   │
│  │  - Application Load Balancer                            │   │
│  │  - NAT Gateways                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            PRIVATE SUBNETS (10.0.10.0/24, 10.0.11.0/24) │   │
│  │  - ECS Fargate Tasks                                    │   │
│  │  - ElastiCache Redis                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          ISOLATED SUBNETS (10.0.20.0/24, 10.0.21.0/24)  │   │
│  │  - RDS PostgreSQL                                       │   │
│  │  - (AuraDB accessed via VPC Peering / PrivateLink)      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Security Groups

| Security Group | Inbound Rules | Outbound Rules |
|----------------|---------------|----------------|
| `sg-alb` | 443 from 0.0.0.0/0 | All to `sg-ecs` |
| `sg-ecs` | 8000 from `sg-alb` | All to `sg-rds`, `sg-redis`, Internet (for Bedrock/AuraDB) |
| `sg-rds` | 5432 from `sg-ecs` | None |
| `sg-redis` | 6379 from `sg-ecs` | None |

---

## 5. Cost Estimation (Monthly)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| **Neo4j AuraDB** | Professional, 8GB RAM, 32GB storage | $325/month |
| **Amazon Bedrock** | ~500K tokens/day (Claude Sonnet + Haiku) | $150-300/month |
| **ECS Fargate** | 2 tasks (1 vCPU, 2GB each), avg utilization | $60/month |
| **RDS PostgreSQL** | db.t3.small, Multi-AZ | $50/month |
| **ElastiCache Redis** | cache.t3.micro | $15/month |
| **CloudFront + S3** | 100GB transfer, 1M requests | $15/month |
| **ALB** | Standard usage | $25/month |
| **Secrets Manager** | 5 secrets | $2/month |
| **CloudWatch** | Standard logging + metrics | $20/month |
| **Total** | | **~$660-810/month** |

*Note: Costs assume moderate usage (50-100 queries/day). Production scaling will increase Bedrock costs proportionally.*

---

## 6. Migration Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Phase 1: Foundation** | Week 1-2 | VPC setup, RDS/ElastiCache provisioning, CI/CD pipelines |
| **Phase 2: Data Migration** | Week 3 | Neo4j → AuraDB migration, data validation |
| **Phase 3: API Migration** | Week 4-5 | ECS deployment, Bedrock integration, load testing |
| **Phase 4: Frontend** | Week 6 | S3/CloudFront deployment, DNS cutover |
| **Phase 5: Validation** | Week 7-8 | End-to-end testing, performance benchmarking, UAT |

---

## 7. Rollback Strategy

1. **Database:** AuraDB supports point-in-time recovery; local Neo4j backup retained for 30 days
2. **API:** Blue-green deployment via ALB target groups; instant rollback
3. **LLM:** Feature flag to switch between Bedrock and Ollama (if self-hosted fallback needed)
4. **Frontend:** CloudFront versioned deployments; rollback via S3 object versioning

---

## 8. Success Criteria

| Metric | V1 Baseline | V2 Target |
|--------|-------------|-----------|
| API Latency (p95) | 15s | < 5s |
| Cypher Query Accuracy | 85% | > 95% |
| Availability | ~95% (local) | 99.9% |
| Concurrent Users | 3 | 50+ |
| Deployment Time | Manual (~1hr) | Automated (< 10min) |

---

## Appendix A: Alternative Cloud Providers

### Azure Option
- **LLM:** Azure OpenAI Service (GPT-4o / GPT-4o-mini)
- **Graph DB:** Neo4j on Azure Marketplace OR Azure Cosmos DB (Gremlin API)
- **Compute:** Azure Container Apps
- **Estimated Cost:** ~$700-900/month

### GCP Option
- **LLM:** Vertex AI (Gemini Pro)
- **Graph DB:** Neo4j on GCP Marketplace
- **Compute:** Cloud Run
- **Estimated Cost:** ~$600-800/month

**Recommendation:** AWS preferred due to Bedrock's Claude models (superior for code generation) and Neo4j AuraDB's native AWS integration.

---

*Document approved for Gemini Pro review and V2 implementation planning.*
