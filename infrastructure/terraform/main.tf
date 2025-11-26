# LLM Orchestration Engine - Terraform Configuration
# AWS Infrastructure as Code

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Uncomment for remote state storage
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "llm-orchestration/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

# ============================================
# Variables
# ============================================

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "llm-orchestration"
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

# ============================================
# Provider Configuration
# ============================================

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ============================================
# Data Sources
# ============================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ============================================
# Local Values
# ============================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
}

# ============================================
# DynamoDB Table - Request Logs
# ============================================

resource "aws_dynamodb_table" "request_logs" {
  name         = "${local.name_prefix}-logs"
  billing_mode = "PAY_PER_REQUEST"  # On-demand for cost efficiency
  hash_key     = "request_id"
  range_key    = "timestamp"
  
  attribute {
    name = "request_id"
    type = "S"
  }
  
  attribute {
    name = "timestamp"
    type = "S"
  }
  
  attribute {
    name = "model"
    type = "S"
  }
  
  # GSI for querying by model
  global_secondary_index {
    name            = "model-index"
    hash_key        = "model"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
  
  # TTL for automatic cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Name = "${local.name_prefix}-logs"
  }
}

# ============================================
# DynamoDB Table - Async Jobs
# ============================================

resource "aws_dynamodb_table" "async_jobs" {
  name         = "${local.name_prefix}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"
  
  attribute {
    name = "job_id"
    type = "S"
  }
  
  attribute {
    name = "status"
    type = "S"
  }
  
  # GSI for querying by status
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  tags = {
    Name = "${local.name_prefix}-jobs"
  }
}

# ============================================
# S3 Bucket - Async Outputs
# ============================================

resource "aws_s3_bucket" "outputs" {
  bucket = "${local.name_prefix}-outputs-${local.account_id}"
  
  tags = {
    Name = "${local.name_prefix}-outputs"
  }
}

resource "aws_s3_bucket_versioning" "outputs" {
  bucket = aws_s3_bucket.outputs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "outputs" {
  bucket = aws_s3_bucket.outputs.id
  
  rule {
    id     = "cleanup-old-outputs"
    status = "Enabled"
    
    expiration {
      days = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "outputs" {
  bucket = aws_s3_bucket.outputs.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ============================================
# SQS Queue - Async Processing
# ============================================

resource "aws_sqs_queue" "processing_queue" {
  name                       = "${local.name_prefix}-processing"
  visibility_timeout_seconds = 300  # 5 minutes for long tasks
  message_retention_seconds  = 86400  # 1 day
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
  
  tags = {
    Name = "${local.name_prefix}-processing"
  }
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name_prefix}-dlq"
  message_retention_seconds = 1209600  # 14 days
  
  tags = {
    Name = "${local.name_prefix}-dlq"
  }
}

# ============================================
# Secrets Manager - API Keys
# ============================================

resource "aws_secretsmanager_secret" "api_keys" {
  name        = "${local.name_prefix}/api-keys"
  description = "API keys for LLM providers"
  
  tags = {
    Name = "${local.name_prefix}-api-keys"
  }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    openai_api_key    = var.openai_api_key
    anthropic_api_key = var.anthropic_api_key
  })
}

# ============================================
# IAM Role - Lambda Execution
# ============================================

resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.request_logs.arn,
          "${aws_dynamodb_table.request_logs.arn}/index/*",
          aws_dynamodb_table.async_jobs.arn,
          "${aws_dynamodb_table.async_jobs.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.outputs.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.processing_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.api_keys.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================
# Outputs
# ============================================

output "dynamodb_logs_table" {
  description = "DynamoDB table for request logs"
  value       = aws_dynamodb_table.request_logs.name
}

output "dynamodb_jobs_table" {
  description = "DynamoDB table for async jobs"
  value       = aws_dynamodb_table.async_jobs.name
}

output "s3_outputs_bucket" {
  description = "S3 bucket for async outputs"
  value       = aws_s3_bucket.outputs.bucket
}

output "sqs_processing_queue" {
  description = "SQS queue for async processing"
  value       = aws_sqs_queue.processing_queue.url
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda"
  value       = aws_iam_role.lambda_role.arn
}
