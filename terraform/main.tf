terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment after manually creating the S3 bucket and DynamoDB table:
  #
  # backend "s3" {
  #   bucket         = "brew-metrics-tfstate"
  #   key            = "brew-metrics/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "brew-metrics-tfstate-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
}
