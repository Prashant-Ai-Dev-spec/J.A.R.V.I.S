# TERRAFORM & INFRASTRUCTURE AS CODE
# 
# J.A.R.V.I.S infrastructure can be deployed on AWS, GCP, Azure, or DigitalOcean.
# Below are placeholders and getting started guides.

## AWS Deployment (Terraform)

# Prerequisites:
# 1. AWS CLI configured with credentials
# 2. Terraform installed
# 3. S3 bucket for Terraform state (recommended)

# File: infra/terraform/aws/main.tf

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "jarvis-terraform-state"      # Change this
    key            = "jarvis/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
}

# Security Group
resource "aws_security_group" "jarvis" {
  name        = "jarvis-sg"
  description = "J.A.R.V.I.S security group"
  vpc_id      = var.vpc_id

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # TURN (UDP)
  ingress {
    from_port   = 3478
    to_port     = 3478
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # TURN TLS (TCP)
  ingress {
    from_port   = 5349
    to_port     = 5349
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "jarvis-sg"
  }
}

# EC2 Instance (t3.medium recommended)
resource "aws_instance" "jarvis" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.jarvis.key_name
  vpc_security_group_ids = [aws_security_group.jarvis.id]
  subnet_id              = var.subnet_id

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 50
    delete_on_termination = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    domain           = var.domain
    admin_api_key    = var.admin_api_key
    docker_compose   = file("${path.module}/docker-compose.prod.yml")
  }))

  tags = {
    Name = "jarvis-instance"
  }
}

# Elastic IP
resource "aws_eip" "jarvis" {
  instance = aws_instance.jarvis.id
  domain   = "vpc"

  tags = {
    Name = "jarvis-eip"
  }
}

# Route53 DNS (optional)
resource "aws_route53_record" "jarvis" {
  zone_id = var.route53_zone_id
  name    = var.domain
  type    = "A"
  ttl     = 300
  records = [aws_eip.jarvis.public_ip]
}

# Output
output "public_ip" {
  value       = aws_eip.jarvis.public_ip
  description = "Public IP of J.A.R.V.I.S instance"
}

output "instance_id" {
  value       = aws_instance.jarvis.id
  description = "EC2 Instance ID"
}
```

# Variables: infra/terraform/aws/variables.tf

```hcl
variable "aws_region" {
  default = "us-east-1"
}

variable "instance_type" {
  default = "t3.medium"
}

variable "vpc_id" {
  description = "VPC ID where instance will be deployed"
}

variable "subnet_id" {
  description = "Subnet ID for the instance"
}

variable "domain" {
  description = "Domain name for J.A.R.V.I.S"
  default     = "jarvis.example.com"
}

variable "admin_api_key" {
  description = "Admin API key"
  sensitive   = true
}

variable "route53_zone_id" {
  description = "Route53 zone ID for DNS management"
  default     = ""
}
```

# Usage:
# 1. cd infra/terraform/aws
# 2. terraform init
# 3. terraform plan -var-file="prod.tfvars"
# 4. terraform apply -var-file="prod.tfvars"

---

## GCP Deployment (Terraform)

# Similar structure for Google Cloud:
# - Use google_compute_instance
# - Use google_compute_firewall for security rules
# - Use google_dns_record_set for DNS

# File: infra/terraform/gcp/main.tf
# (Template provided in gcp/ directory)

---

## DigitalOcean Deployment

# Using Terraform:
# - Use digitalocean_droplet for compute
# - Use digitalocean_firewall for security
# - Use digitalocean_record for DNS

# Or App Platform (managed):
# - Deploy directly from Docker Compose
# - Automatic scaling, SSL, monitoring included

---

## Azure Deployment

# Using Terraform:
# - Use azurerm_linux_virtual_machine
# - Use azurerm_network_security_group
# - Use azurerm_dns_zone

---

## LOCAL DEPLOYMENT (Testing)

# For local testing with self-signed certificates:
# 1. Run: ./scripts/create_selfsigned_cert.ps1 (Windows) or get_cert.sh (Linux)
# 2. Certificates created in backend/certs/
# 3. Start: docker-compose up -d
# 4. Test: https://127.0.0.1 (ignore cert warning)

---

## NEXT STEPS:

1. Choose your cloud provider (AWS recommended for simplicity)
2. Fill in terraform/[provider]/terraform.tfvars with:
   - vpc_id / network settings
   - domain name
   - admin API key
   - SSH key name
3. Run: terraform init && terraform plan && terraform apply
4. Update DNS to point to instance
5. SSH in and verify containers running
6. Access https://yourdomain.com/meeting

# For production, also configure:
- CloudFront (AWS) / CDN for static assets
- S3 / Cloud Storage for audit log archives
- CloudWatch / StackDriver for monitoring
- SNS / Cloud Alerts for notifications
