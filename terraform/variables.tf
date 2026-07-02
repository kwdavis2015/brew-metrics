variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix used for all resource names"
  type        = string
  default     = "brew-metrics"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "brewadmin"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "admin_username" {
  description = "Admin portal username"
  type        = string
  default     = "admin"
}

variable "admin_password" {
  description = "Admin portal password"
  type        = string
  sensitive   = true
}

variable "app_image_tag" {
  description = "ECR image tag to deploy on ECS"
  type        = string
  default     = "latest"
}
