output "api_url" { value = "http://${aws_lb.app.dns_name}" }
output "cloudfront_url" { value = "https://${aws_cloudfront_distribution.site.domain_name}" }
output "ecr_repository_url" { value = aws_ecr_repository.app.repository_url }
output "import_bucket" { value = aws_s3_bucket.imports.id }
output "statistics_bucket" { value = aws_s3_bucket.site.id }
output "ecs_cluster" { value = aws_ecs_cluster.main.name }
output "ecs_service" { value = aws_ecs_service.app.name }
output "database_endpoint" { value = aws_db_instance.orders.address }
output "database_secret_arn" { value = aws_db_instance.orders.master_user_secret[0].secret_arn }
output "github_deploy_role_arn" {
  value = try(aws_iam_role.github_deploy[0].arn, null)
}
