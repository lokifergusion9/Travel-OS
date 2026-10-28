variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "project" {
  type    = string
  default = "travelos"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "db_username" {
  type    = string
  default = "travelos"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

# Container image URIs (set after first ECR push; the Deploy workflow updates tags).
variable "backend_image" {
  type    = string
  default = ""
}

variable "desired_web_count" {
  type    = number
  default = 2
}

# App secrets injected via Secrets Manager (see secrets in main.tf).
variable "app_secret_key" {
  type      = string
  sensitive = true
}

variable "credentials_encryption_key" {
  type      = string
  sensitive = true
}

variable "cors_origins" {
  type    = string
  default = "https://app.example.com"
}
