resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7

  tags = {
    Project = var.project_name
  }
}

# NOTE: aws_ecs_express_gateway_service requires AWS provider >= 6.0.
# Known issue: first apply may fail with "Provider produced inconsistent result after apply".
# Workaround if it occurs:
#   terraform state rm aws_ecs_express_gateway_service.app
#   terraform import aws_ecs_express_gateway_service.app <service-arn>
resource "aws_ecs_express_gateway_service" "app" {
  service_name            = var.project_name
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  infrastructure_role_arn = aws_iam_role.ecs_infrastructure.arn
  task_role_arn           = aws_iam_role.ecs_task.arn

  primary_container {
    image          = "${aws_ecr_repository.app.repository_url}:${var.app_image_tag}"
    container_port = 8080

    aws_logs_configuration {
      log_group         = aws_cloudwatch_log_group.app.name
      log_stream_prefix = "ecs"
    }

    environment {
      name  = "SECRET_NAME_DB"
      value = aws_secretsmanager_secret.db_credentials.name
    }
    environment {
      name  = "SECRET_NAME_ADMIN"
      value = aws_secretsmanager_secret.admin_credentials.name
    }
    environment {
      name  = "AWS_REGION"
      value = var.aws_region
    }
  }

  health_check_path = "/"
  cpu               = "256"
  memory            = "512"

  scaling_target {
    min_task_count            = 1
    max_task_count            = 2
    auto_scaling_metric       = "AVERAGE_CPU"
    auto_scaling_target_value = 70
  }

  network_configuration {
    subnets         = aws_subnet.public[*].id
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  tags = {
    Project = var.project_name
  }
}
