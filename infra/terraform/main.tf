data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }

locals {
  name = var.project
  azs  = slice(data.aws_availability_zones.available.names, 0, 2)
}

# --- Network (VPC module) ---
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = "${local.name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets   = [cidrsubnet(var.vpc_cidr, 8, 0), cidrsubnet(var.vpc_cidr, 8, 1)]
  private_subnets  = [cidrsubnet(var.vpc_cidr, 8, 10), cidrsubnet(var.vpc_cidr, 8, 11)]
  database_subnets = [cidrsubnet(var.vpc_cidr, 8, 20), cidrsubnet(var.vpc_cidr, 8, 21)]

  enable_nat_gateway     = true
  single_nat_gateway     = true
  create_database_subnet_group = true
}

# --- Container registry ---
resource "aws_ecr_repository" "backend" {
  name                 = "${local.name}-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${local.name}-frontend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

# --- Secrets ---
resource "aws_secretsmanager_secret" "app" {
  name = "${local.name}/app"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    SECRET_KEY                 = var.app_secret_key
    CREDENTIALS_ENCRYPTION_KEY = var.credentials_encryption_key
    DATABASE_URL               = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/${local.name}"
    REDIS_URL                  = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
  })
}
