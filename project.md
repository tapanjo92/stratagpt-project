# Australian‑Strata GPT – Project Blueprint

*Living technical specification — last revised 20 Jun 2025*

> **Scope of this document** – serves as a single source of truth for product, architecture, DevOps, security, and commercial planning. All teams (engineering, product, infosec, finance, customer success) should reference this living spec before making material changes.

---

## 1  Vision & Business Context

Strata management in Australia is governed by complex state legislation (Strata Schemes Management Act 2015 for NSW, Body Corporate and Community Management Act 1997 for QLD, etc.). Committees, lot owners and managing agents waste time hunting through minutes, by‑laws, special resolutions and Fair‑Trading circulars. **Australian‑Strata GPT** turns those unstructured archives into a question‑answer service with legal‑grade citations.

* **Target market** – professional strata managers (tier‑1 + boutique), self‑managed bodies corporate, and legal advisers.
* **Personas** – Strata Manager (SM), Committee Secretary (CS), Lot Owner (LO), Service Contractor (SC).
* **Value prop** – reduce email volume by 40 %, cut document‑lookup time from 15 min to < 30 s, improve by‑law compliance.

### Success metrics (first 12 months)

| KPI                    | Definition                           | Target |
| ---------------------- | ------------------------------------ | ------ |
| Daily Active Buildings | # buildings with ≥ 1 chat query      | 500    |
| Answer Accuracy        | Manual audit “correct + fully cited” | ≥ 92 % |
| P95 Latency            | End‑to‑end TTFB (Sydney)             | < 2 s  |
| Gross Margin           | (Revenue – COGS)/Revenue             | ≥ 80 % |
| Churn                  | Buildings cancelling after 6 mo      | < 3 %  |

---

## 2  Architecture Overview

### 2.1 High‑Level Diagram

```mermaid
flowchart TD
  subgraph Edge
    A[Browser / Mobile]-->CF[Amazon CloudFront]
  end
  subgraph UI
    CF-->ALB[Application Load Balancer]
    ALB-->ECS[Fargate Service\nNext.js SSR + RTC]
    ECS-.Auth.->COG[Cognito User Pools]
  end
  subgraph API
    ECS-->AGW[API Gateway REST]
    AGW-->LAMBDA[Chat Resolver Lambda\n(Python + Powertools)]
    LAMBDA-->BEDROCK[Bedrock Agent\n(Knowledge Bases)]
  end
  subgraph Retrieval
    BEDROCK-->KENDRA[Kendra GenAI Index]
    KENDRA<-->OS[OpenSearch Vector DB]
  end
  subgraph Ingest
    S3[S3 Secure Uploads]-->EVB(EventBridge Rule)
    EVB-->SFN[Step Functions State Machine]
    SFN-->TEX[Textract OCR]
    SFN-->LANG[Chunk & Sanitise Lambda]
    LANG-->EMB[Titan Embeddings]
    EMB-->OS
  end
  COG-->DDB[DynamoDB (Multi‑tenant Meta)]
  AGW-->DDB
```

### 2.2 Detailed Data Flow

1. **Upload (≤ 250 MB/file)** – encrypted PUT to tenant‑scoped S3 prefix; presigned URL expires in 15 min.
2. **Ingestion pipeline** – Step Functions parallel branch per document:

   * *Textract →* JSON‑encoded lines, tables, forms.
   * *Chunk Lambda* – adaptive 1 000‑token window, overlaps 200 tokens, proprietary redaction (PII, signatures).
   * *Embeddings* – Bedrock Titan V2 768‑dim vectors; namespace = `tenantId/documentId`.
   * *Index write* – vector + metadata JSON to OpenSearch *and* reference to Kendra Index.
3. **Query path** – signed JWT from Cognito hits `/chat` on API GW; Lambda resolver:

   ```python
   top_k = kb.retrieve(question, tenant_id, k=10)
   answer = kb.generate(question, top_k, model_alias="claude3-opus")
   stream(answer)
   ```
4. **Response delivery** – Server‑Sent‑Events (SSE) stream through API GW; React client renders Markdown w/ citation tooltips.

---

## 3  Service Matrix & Operational Notes

| Layer         | AWS Service    | Quotas & Config                                 | Ops Guardrails                       |
| ------------- | -------------- | ----------------------------------------------- | ------------------------------------ |
| UI & Edge     | CloudFront     | ORIGIN\_SHIELD in ap‑southeast‑2                | WAF geo‑block non‑ANZ by default     |
|               | ALB            | 2 subnets, idle timeout 120 s                   | Shield Adv. in prod                  |
|               | ECS Fargate    | `cpu=0.25–2`, `memory=0.5–4GiB`                 | Auto‑scale on ALB Req/s              |
| Auth          | Cognito        | SRP + OAuth2, 2‑FA optional                     | Rotate app‑client secrets quarterly  |
| API           | API Gateway    | Throttle = 100r/s burst 500                     | WAF Bot‑Ctrl rule set                |
| Serverless    | Lambda         | `python3.12`, `memory=1 024 MB`, `timeout=30 s` | Powertools logger, idempotency layer |
| Retrieval     | Bedrock Agent  | Model alias param in SSM                        | Prompt cache TTL = 30 days           |
|               | Kendra GenAI   | Index storage 100 GB/start                      | Synonym lists per state legislation  |
|               | OpenSearch     | UltraWarm disabled, snapshots daily             | Fine‑grained tenant role mapping     |
| Ingest        | Textract       | 1 000 p/min soft quota                          | Audit anomalies via Macie            |
|               | Step Functions | Standard WF, `retry: 2, backoff 2x`             | DLQ SNS alarm                        |
| Data          | DynamoDB       | GSIs: `TenantByDate`, `InvoiceByTenant`         | On‑demand capacity + PITR            |
| Observability | CloudWatch     | Logs retained 365 d                             | Metric filters: `ERROR`, `THROTTLED` |
|               | X‑Ray          | 100 % sampling on staging, 10 % prod            | SQS alarm on 5xx spikes              |

---

## 4  Feature Catalogue (v1)

| #  | Group         | Feature                                           | Persona  | Status     |
| -- | ------------- | ------------------------------------------------- | -------- | ---------- |
| A1 | Chat          | Natural‑language Q\&A with clause‑level citations | LO/CS/SM | ✅ In dev   |
| A2 | Chat          | Role‑aware explanations (owner vs manager)        | SM/CS    | 🔄 Backlog |
| B1 | Ingest        | Drag‑drop upload (PDF, DOCX, TIFF)                | SM       | ✅          |
| B2 | Ingest        | Bulk import from Google Drive                     | SM       | 🔄         |
| B3 | Ingest        | Version detection & diff                          | SM       | 🔄         |
| C1 | Smart actions | Generate levy reminder template                   | SM       | ✅          |
| C2 | Smart actions | AGM minute summary in 200 words                   | SM/CS    | 🔄         |
| D1 | Tenancy       | Custom sub‑domain & branding                      | SM       | ✅          |
| F1 | Compliance    | 7‑year immutable log (S3 Glacier)                 | SM       | ✅          |
| H1 | Integrations  | REST/GraphQL API key SDK                          | Dev      | ✅          |
| J1 | Ops           | Live status page (StatusCake)                     | All      | 🔄         |

Legend: ✅ = in sprint; 🔄 = backlog; 🟦 = future.

---

## 5  CI/CD & Release Management

```text
Git push → CodePipeline
  ├─ Build (CodeBuild) ──┐            # npm ci, linters, unit tests
  │                      ├─ docker build → ECR
  │                      └─ cdk synth → cdk.out
  ├─ Security scan (Trivy)             # block CVSS ≥ 7.0
  ├─ Deploy Test (CodeDeploy) → ECS    # blue task‑set
  ├─ Smoke tests (Synthetics Canary)   # 20 endpoints
  ├─ Manual approval (Slack)           # product owner OK
  └─ Prod Cutover → ALB prod listener  # auto‑rollback on 5xx > 2 %
```

*Versioning* – Git tags `vYY.MM.dd‑n`. *Rollback* – one‑click to previous task‑set.

---

## 6  Delivery Roadmap (8 Sprints, 2 w each)

| Sprint | Maturity Goal            | Milestones & Artefacts                                                       |
| ------ | ------------------------ | ---------------------------------------------------------------------------- |
| 1      | *Ingestion MVP*          | S3 bucket, Textract + Embedding Lambda, OpenSearch index, smoke test script. |
| 2      | *RAG Core*               | Kendra GenAI index, Bedrock Agent KB, evaluation harness (20 Q\&A pairs).    |
| 3      | *Chat API*               | Lambda resolver, SSE stream, JSON schema, Postman collection.                |
| 4      | *UI Alpha*               | Next.js chat widget, Cognito auth, local dev storybook.                      |
| 5      | *Billing & Multitenancy* | DynamoDB schema, Stripe webhook, admin dashboard v0.                         |
| 6      | *Observability*          | CW dashboards, X‑Ray maps, cost anomaly alarms.                              |
| 7      | *Security Hardening*     | WAF OWASP rules, Macie PII audit, pentest sign‑off.                          |
| 8      | *Production Launch*      | Blue‑green cutover, Route 53, post‑launch load test (k6 500 VU).             |

---

## 7  Operations Handbook (Day‑2)

| Dimension        | SRE Action                                      | SLA / Target      |
| ---------------- | ----------------------------------------------- | ----------------- |
| **Availability** | Min 2 tasks across 2 AZ; auto‑heal < 5 min      | 99.9 % month      |
| **Latency**      | Alarm P95 > 2 s for 5 min                       | Restore in 30 min |
| **Capacity**     | Scale ECS when CPU > 60 % or ALB RPS > 50       | —                 |
| **Security**     | Rotate KMS CMKs yearly; patch base image weekly | Zero CVE > 7      |
| **Backup**       | OpenSearch snapshot 24h; DynamoDB PITR 35 d     | —                 |
| **Incident**     | PagerDuty Sev‑1: 15 min acknowledgement         | —                 |

---

## 8  Cost & Revenue Model (v1‑draft)

### 8.1 COGS Breakdown @ 10 k lots / month

| Item                  | Qty           | Rate         | Cost (AUD) |
| --------------------- | ------------- | ------------ | ---------- |
| Fargate vCPU‑h        | 3 600         | \$0.0404     | 145.4      |
| Textract pages        | 200 000       | \$0.0125     | 2 500      |
| Bedrock tokens (Q\&A) | 120 M         | \$0.00075/1k | 90         |
| Bedrock embeddings    | 48 M          | \$0.0008/1k  | 38         |
| Kendra index          | 720 h         | \$0.14       | 101        |
| OpenSearch cluster    | 2 × r6g.large | —            | 330        |
| S3 storage            | 2 TB          | \$0.0308/GB  | 61         |
| **Total COGS**        |               |              | **3 265**  |

### 8.2 P\&L Snapshot

*Revenue* = 10 k lots × \$2 = **\$20 000** → *Gross Margin* ≈ **83 %**.
Breakeven (OPEX ≈ \$35 k) at \~25 k lots.

---

## 9  Forward‑Looking Enhancements

1. **Realtime WebSocket chat** – cut latency < 300 ms; needed for mobile‑app typing preview.
2. **Multilingual LLM routing** – auto‑detect language, switch to Bedrock Titan Translate.
3. **BYO‑Model** – legal‑domain fine‑tuned LLM via Bedrock custom import.
4. **Embedded QuickSight** – board dashboard: open maintenance items, levy arrears.
5. **Cross‑index legislation** – toggle to query state legislation corpus alongside building docs.

---

## 10  References

* AWS Blog – *Kendra GenAI Index announced* (2025‑05)
* AWS News – *Bedrock Intelligent Prompt Routing* (2024‑12)
* AWS Docs – *ECS Blue/Green deployments with CodeDeploy*
* NSW Fair Trading – *Strata Legislation PDFs*

---

**End of Document**

