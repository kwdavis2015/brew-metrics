resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}/db-credentials"
  description = "RDS Postgres credentials and connection URL"

  tags = {
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = aws_db_instance.postgres.address
    port     = 5432
    dbname   = "brewmetrics"
    url      = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/brewmetrics"
  })
}

resource "aws_secretsmanager_secret" "admin_credentials" {
  name        = "${var.project_name}/admin-credentials"
  description = "Admin portal login credentials"

  tags = {
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "admin_credentials" {
  secret_id = aws_secretsmanager_secret.admin_credentials.id
  secret_string = jsonencode({
    username    = var.admin_username
    password    = var.admin_password
    dossier_key = var.dossier_key
  })
}
