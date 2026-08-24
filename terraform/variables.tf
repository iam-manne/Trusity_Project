variable "project_name" {
  type    = string
  default = "order-service"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "aws_region" {
  type    = string
  default = "ap-south-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "container_image" {
  type        = string
  description = "Immutable ECR image URI including a tag or digest"
  default     = "REQUIRED_FOR_FULL_APPLY"
}

variable "desired_count" {
  type    = number
  default = 2
}

variable "min_capacity" {
  type    = number
  default = 2
}

variable "max_capacity" {
  type    = number
  default = 6
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_multi_az" {
  type        = bool
  description = "Enable for staging/production; false minimizes assessment cost"
  default     = false
}

variable "alarm_email" {
  type        = string
  description = "Optional alarm subscription email"
  default     = ""
}

variable "lambda_package_path" {
  type    = string
  default = "../lambda_bulk_import/bulk-import.zip"
}

variable "github_repository" {
  type        = string
  description = "GitHub owner/repository allowed to deploy; empty disables CI role creation"
  default     = ""
}

variable "create_github_oidc_provider" {
  type        = bool
  description = "Create account-wide GitHub OIDC provider; false when it already exists"
  default     = false
}
