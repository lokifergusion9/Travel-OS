# TravelOS — Terraform

Provisions the AWS stack: VPC, ECR, RDS Postgres (pgvector), ElastiCache Redis,
S3 + CloudFront (asset CDN), ALB, ECS Fargate (web + worker + migrate), IAM, and
Secrets Manager.

```bash
cp terraform.tfvars.example terraform.tfvars   # fill in secrets
terraform init
terraform plan
terraform apply
```

This is a **starter skeleton** — review before production use. In particular:
- Add an HTTPS (443) listener with an ACM certificate; redirect 80 → 443.
- Configure an S3 remote state backend (see `versions.tf`).
- After `apply`, run the one-time DB bootstrap (create `travelos_app` role +
  `CREATE EXTENSION vector`) — see `docs/DEPLOY.md` §2b.
- Tighten egress security-group rules and enable RDS multi-AZ / deletion
  protection for real workloads.

Full walkthrough: `docs/DEPLOY.md`.
