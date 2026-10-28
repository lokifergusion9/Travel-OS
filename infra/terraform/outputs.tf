output "alb_dns_name" {
  description = "Public DNS of the application load balancer (point your domain here)."
  value       = aws_lb.this.dns_name
}

output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "assets_cdn_domain" {
  value = aws_cloudfront_distribution.assets.domain_name
}

output "assets_bucket" {
  value = aws_s3_bucket.assets.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "ecs_cluster" {
  value = aws_ecs_cluster.this.name
}
