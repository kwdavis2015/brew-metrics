output "ecr_repository_url" {
  description = "ECR repository URL — use this for docker tag and docker push"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_service_url" {
  description = "ECS Express Mode public HTTPS URL"
  value       = aws_ecs_express_gateway_service.app.service_url
}

output "rds_endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}
