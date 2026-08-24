# End-to-end recording checklist

Record terminal commands and AWS console pages without exposing secrets, account IDs, customer data, or credentials. Keep the recording short but show evidence in this order:

1. Show the GitHub Actions run: test/lint, image build, Trivy scan, ECR push, new task registration, and stable ECS deployment. Show the SHA image tag in ECR.
2. Show Terraform outputs and the ECS service with at least two running tasks distributed across two Availability Zones. Show the private subnet assignment and ALB's healthy targets.
3. Call `POST /orders`; retain the returned ID. Call `GET /orders/{id}`, `GET /orders`, and `/health`, showing HTTP status and JSON.
4. Upload `examples/orders.csv` to `s3://<import-bucket>/uploads/demo.csv`. Show the Lambda invocation/log stream, the generated `import-reports/*.json`, and that the invalid row failed while valid rows were inserted.
5. Connect through an approved private path (ECS Exec/SSM or a read-only database tool in the VPC) and query the new API and imported rows. Do not display the secret.
6. Run the statistics generator from a VPC-reachable runner, upload `index.html`, open the CloudFront URL, and show totals/top product.
7. Show CloudWatch application and Lambda logs, ALB/ECS/RDS metrics, and the configured 5xx, CPU, and Lambda alarms.
8. Start a loop calling `/health` and `/orders`. Stop one ECS task with an `assessment-drill` reason. Show requests continuing, the target becoming unhealthy, ECS launching a replacement, desired count returning, and related events/metrics.
9. Show the current and previous ECS task revisions. Explain that the circuit breaker rejects unhealthy tasks; demonstrate the manual rollback script or a workflow dispatch with the prior SHA in the non-production environment.

Before submission, include the repository link and recording link, verify access from a private/incognito browser, remove generated state/secrets, and ensure all required evidence above is visible.
