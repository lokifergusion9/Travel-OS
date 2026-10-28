terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
  # Configure remote state before real use:
  # backend "s3" { bucket = "..." key = "travelos/terraform.tfstate" region = "ap-south-1" }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project = "TravelOS"
      Managed = "terraform"
    }
  }
}
