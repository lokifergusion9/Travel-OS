# Deploy TravelOS on AWS Free Tier (one box, ~3-day demo)

Runs the whole stack on a single free-tier EC2 instance with Docker. No RDS /
ALB / NAT — so it stays within the free tier. Runs **keyless** (built-in mocks),
so no API keys are needed. Plan ~20–30 minutes the first time.

> 💸 **Money safety:** the free tier covers a `t2.micro`/`t3.micro` for 750
> hrs/month for 12 months and 30 GB storage. To avoid any charge after the demo,
> **stop or terminate the instance** (see §10) and keep the budget alarm (§3).

---

## 1. Create an AWS account
1. Go to https://aws.amazon.com → **Create an AWS Account**.
2. Enter email, account name, verify, set a strong root password.
3. Add a payment card (required even for free tier — you won't be charged if you
   stay in free tier and tear down after).
4. Verify phone, choose the **Basic (free) support plan**.
5. Sign in to the **AWS Management Console**. Top-right, pick a region near you,
   e.g. **Asia Pacific (Mumbai) ap-south-1**. Keep the same region throughout.

## 2. (Recommended) Make a non-root admin user
Using root for daily work is discouraged, but for a 3-day demo it's acceptable.
If you want to be tidy: IAM → Users → Create user → attach `AdministratorAccess`
→ sign in as that user. Otherwise continue as root.

## 3. Set a budget alarm (do this!)
Billing → **Budgets** → Create budget → **Zero spend budget** (or set $1) → add
your email. You'll get an alert if anything ever costs money.

## 4. Launch a free-tier EC2 instance
EC2 → **Instances** → **Launch instances**:
- **Name:** `travelos-demo`
- **AMI:** *Amazon Linux 2023* (free-tier eligible)
- **Instance type:** `t2.micro` (or `t3.micro`) — “Free tier eligible”
- **Key pair:** Create one (e.g. `travelos-key`), download the `.pem` — you'll
  SSH with it. (Or skip and use EC2 Instance Connect in the browser.)
- **Network settings → Edit → Security group**, allow:
  - **SSH (22)** — Source: *My IP*
  - **HTTP (80)** — Source: *Anywhere (0.0.0.0/0)*
- **Storage:** bump to **30 GiB gp3** (free tier covers 30 GB).
- **Launch instance.** Open it and copy the **Public IPv4 address**.

## 5. Connect to the instance
Easiest: select the instance → **Connect** → **EC2 Instance Connect** → Connect
(opens a browser terminal). Or from your Mac:
```bash
chmod 400 ~/Downloads/travelos-key.pem
ssh -i ~/Downloads/travelos-key.pem ec2-user@<PUBLIC_IP>
```

## 6. Install Docker + swap
```bash
sudo dnf -y install git
git clone https://<YOUR_GH_USERNAME>:<YOUR_PAT>@github.com/lokifergusion9/TravelOS.git TravelOS
cd TravelOS
bash deploy/aws-free-tier/bootstrap.sh
# bootstrap installs Docker + Compose and adds 4 GB swap (needed on 1 GB RAM)
newgrp docker     # apply the docker group without logging out
```
> **PAT:** the repo is private, so clone with a token. GitHub → Settings →
> Developer settings → **Fine-grained tokens** → generate one with *Contents:
> Read* on this repo, and use it in the clone URL above. (Or make the repo
> public for the demo.)

## 7. Configure secrets
```bash
cd ~/TravelOS/deploy/aws-free-tier
cp .env.example .env
# generate the two secrets:
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "CREDENTIALS_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')"
nano .env     # paste those two values in, save (Ctrl+O, Enter, Ctrl+X)
```

## 8. Build & launch
```bash
docker compose up -d --build
```
First build takes ~10–15 min on a micro instance (it's compiling/downloading
deps and building the SPA — swap makes this possible). Watch progress:
```bash
docker compose logs -f web        # Ctrl+C to stop following
docker compose ps                 # all should be "Up" / "healthy"
```

## 9. Open it
Visit **http://&lt;PUBLIC_IP&gt;** in your browser. Sign up → onboarding →
Trips → generate an itinerary + creatives → Leads/Sourcing/Publishing/Analytics.
Everything works with mock AI — zero keys.

(Want real AI output? Add a free `GEMINI_API_KEY` to `.env` plus
`LLM_TEXT_PROVIDER=gemini`, `LLM_IMAGE_PROVIDER=gemini`, then
`docker compose up -d`.)

---

## 10. Tear down when the demo is over (avoid charges)
- **Pause (resume later):** EC2 → select instance → **Instance state → Stop**.
  (Stopped = no compute cost; the 30 GB EBS is within free tier.)
- **Delete everything:** **Instance state → Terminate**. Then check EC2 →
  Volumes and delete any leftover volume, and Budgets shows $0.

## Troubleshooting
- **Build killed / OOM:** confirm swap is on (`free -h` shows ~4 GB swap). Re-run
  `bash deploy/aws-free-tier/bootstrap.sh`.
- **Site won't load:** security group must allow port 80 from anywhere;
  `docker compose ps` should show `frontend` Up; `docker compose logs frontend`.
- **502 from nginx:** the web container is still migrating/starting —
  `docker compose logs web` until you see Gunicorn “Listening at”.
- **Reset DB:** `docker compose down -v && docker compose up -d --build`.
