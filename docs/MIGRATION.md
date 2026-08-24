# Serverless-to-container migration plan

## Scope and target state

Assumed current state: API Gateway invokes synchronous Lambda handlers; DynamoDB or a serverless relational store holds orders; S3 events invoke a bulk-import Lambda; CloudWatch stores logs and metrics; environment variables/Parameter Store or Secrets Manager supply configuration. Discovery must confirm actual APIs, event schemas, data volume, consistency requirements, quotas, dependencies, IAM grants, SLOs, peak traffic, and recovery objectives before implementation.

The target moves the synchronous order API and core processing runtime to stateless containers on ECS Fargate behind an ALB. It retains managed services where they remain a good fit: RDS PostgreSQL for data, S3 and Lambda for bursty file ingestion, ECR, Secrets Manager, CloudFront, CloudWatch, and Route 53. Retaining the event-driven importer avoids paying for idle workers and isolates untrusted batch input from the API fleet. Fargate removes host management while providing image, runtime, network, scaling, and deployment control.

| Current component | Target | Treatment and reason |
|---|---|---|
| API Gateway | ALB (optionally API Gateway in front for API keys/quotas) | Migrate routing to ALB; retain API Gateway only if its edge controls are required. |
| Synchronous API Lambdas | FastAPI containers on ECS Fargate | Migrate business logic into a versioned image and scale as a service. |
| Background/event Lambdas | Lambda or SQS-backed ECS workers | Retain short, bursty S3 importer; move long-running/high-steady-volume handlers to workers. |
| DynamoDB/serverless DB | RDS PostgreSQL | Migrate when relational transactions/reporting are required; retain DynamoDB if access patterns and scale make it preferable. |
| S3 object events | S3 event -> Lambda (prefer S3 -> SQS -> Lambda in production) | Retain managed trigger and add buffering/redrive at scale. |
| Lambda concurrency scaling | ECS target tracking and scheduled scaling | Configure tested min/max task counts and deployment capacity. |
| CloudWatch logs/metrics | CloudWatch Logs, Container Insights, ALB/RDS metrics | Retain and add task/deployment/database dashboards and alarms. |
| Lambda environment configuration | ECS task environment + Secrets Manager | Keep non-secrets in versioned task definitions; inject rotated secrets at runtime. |

## Component migration and data

First extract domain logic behind contract tests using captured, sanitized request/event fixtures. Implement the same API schemas and status semantics in the container. Add request IDs and structured logs so responses can be compared across platforms. Package it as a non-root image, scan it, and run it in a non-production ECS environment.

Define the PostgreSQL schema, constraints, indexes, retention, and ownership roles. Use AWS DMS for continuous full-load plus change-data-capture when the source is supported. For DynamoDB, use point-in-time export to S3 for bulk load and DynamoDB Streams into an idempotent replication consumer for changes. Convert types/timestamps explicitly, reconcile row counts and checksums by time/key range, sample business records, and compare aggregate status/product totals. Maintain a source-to-target ID map only if IDs cannot be preserved.

During dual operation, designate one system as writer. Avoid uncontrolled dual writes. Prefer change capture/outbox replication; if the old handler must mirror writes, make the second write idempotent and monitor a reconciliation queue. Freeze destructive schema changes until rollback risk has passed. Back up both stores and perform a timed restore rehearsal.

ECS tasks connect through a restricted security group using a least-privilege database user in Secrets Manager. Size each pool and ECS maximum so aggregate connections remain below an alert threshold (for example 70% of the database limit). Put RDS Proxy between tasks/Lambda and RDS if connection churn or Lambda concurrency can exhaust the database. Enable Multi-AZ, automated backups/PITR, encryption, Performance Insights, and slow-query logging.

## Scaling, security, and observability

Load-test representative reads, writes, large lists, invalid requests, deployments, and database failover. Set minimum tasks for baseline traffic and target tracking on CPU plus request count/latency where appropriate. Pre-scale for known peaks. Test 10x traffic and establish the first limiting dependency: connections, locks/IOPS, memory, NAT, downstream quotas, or queue age. Establish concurrency budgets and backpressure instead of allowing every tier to scale without bounds.

Use private subnets, security-group references, TLS, WAF/rate limits, workload IAM roles, a separate app database role, encrypted data/logs, secret rotation, dependency/image scanning, CloudTrail, and restricted CI OIDC trust. Review old Lambda roles and remove obsolete permissions only after rollback expiry.

Create a shared dashboard for request rate, p50/p95/p99 latency, 4xx/5xx, healthy targets, task restarts, CPU/memory, database connections/CPU/IOPS/locks, replication lag, Lambda errors/throttles/duration, import failures, queue age, and business metrics (accepted/completed/failed orders). Use the same correlation/request ID in old and new paths. Define SLO-based alerts and synthetic create/read canaries.

## Production cutover

1. Establish baseline metrics and acceptance/error budgets on the old stack. Deploy the target dark, restore/replicate data, run contract, load, security, failover, and restore tests.
2. Shadow a sanitized sample of reads to the target without returning its response. Compare status codes, payloads, latency, and database results. Resolve divergences.
3. Start a 1% weighted Route 53 or CloudFront origin shift to the target. Keep writes single-authority and replication current. Hold through at least one representative peak.
4. Advance through 5%, 10%, 25%, 50%, and 100% only when the gate is healthy for the agreed observation period. Reconcile records at every stage and keep the old stack warm.
5. At final write cutover, briefly quiesce order creation if needed, drain/verify replication lag at zero, switch writer authority, validate synthetic create/read/import paths, then resume. Reads can move gradually before writes.
6. After a stable rollback window, stop replication, archive evidence/backups, reduce old capacity, and eventually remove old resources and privileges through a separate approved change.

Compare request volume, success/5xx rates, p95/p99 latency, timeout rate, data lag/count/checksum divergence, order completion/failure rate, queue age, ECS saturation, RDS connections/CPU/IO latency/locks, and cost per order before, during, and after every shift.

Pause advancement for any unexplained contract mismatch, rising replication lag, failed reconciliation, SLO/error-budget breach, security control failure, capacity below tested headroom, or missing observability. Roll back immediately for sustained elevated 5xx/latency, lost/duplicated orders, corrupt data, unavailable dependencies, or inability to diagnose within the incident time box.

## Rollback and post-cutover recovery

For a bad container release, ECS's circuit breaker or an operator restores the prior immutable task revision while the database remains backward compatible. For traffic migration failure, set the weighted route to 0% target/100% old and verify old health. If target writes have begun, stop new writes, preserve logs and snapshots, replay target-only changes back to the old store through the idempotent change stream, reconcile counts/checksums, and only then return old writer authority. Never point both writable systems at users without conflict rules.

If failure occurs after 100% traffic, the incident commander chooses forward repair versus rollback based on data divergence and recovery time. Snapshot the target, retain its event/outbox log, restore or promote the old platform, reverse-replicate acknowledged target orders, and validate synthetic and business totals before reopening writes. Communicate order ranges/time windows requiring manual review. Keep rollback tooling, old capacity, compatible schemas, credentials, and replication operational until the agreed stability window and backup restore have passed.

