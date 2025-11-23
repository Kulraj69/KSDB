# Deployment Guide for KSdb Cloud

## Quick Start (3 Options)

### Option 1: GitHub Actions (Easiest - No Local Docker Needed)

1. **Add GitHub Secrets** (Settings → Secrets and variables → Actions):
   ```
   AWS_ACCESS_KEY_ID: Your AWS access key
   AWS_SECRET_ACCESS_KEY: Your AWS secret key
   DATABASE_URL: sqlite:///data/ksdb_cloud.db
   ADMIN_KEY: $(openssl rand -hex 32)  # Generate secure key
   ```

2. **Trigger Deployment**:
   - Go to: Actions → Deploy KSdb Cloud to AWS → Run workflow
   - Select "production"
   - Click "Run workflow"

3. **Wait 5-10 minutes**, then check the workflow logs for your service URL

---

### Option 2: Local Deployment (Requires Docker Desktop)

```bash
# 1. Start Docker Desktop on your Mac

# 2. Run deployment script
source deploy/.env.aws
bash deploy/deploy_aws.sh
```

---

### Option 3: AWS Console (Manual)

1. **Build locally** (if Docker is running):
   ```bash
   docker build -f Dockerfile.cloud -t ksdb-cloud:latest .
   ```

2. **Push to ECR**:
   - Create ECR repository in AWS Console
   - Follow push commands from ECR

3. **Create App Runner Service**:
   - Go to AWS App Runner
   - Create service from ECR
   - Configure health check: `/health`
   - Add environment variables

---

## Post-Deployment

### Create Your First Tenant

```bash
# Get your service URL from deployment output
export KSDB_URL="https://your-service.us-east-1.awsapprunner.com"
export ADMIN_KEY="your_admin_key_from_secrets"

# Create tenant
curl -X POST "$KSDB_URL/admin/create-tenant?tenant_name=my-org&admin_key=$ADMIN_KEY"

# Save the returned API key!
```

### Test the API

```python
from ksdb import CloudClient

client = CloudClient(
    api_key="ks_live_...",  # From previous step
    url="https://your-service.us-east-1.awsapprunner.com"
)

# Create collection
collection = client.get_or_create_collection("test")

# Add documents
collection.add(
    ids=["1", "2"],
    documents=["Hello KSdb Cloud!", "It works!"]
)

# Search
results = collection.query(query_texts=["hello"], n_results=5)
print(results)
```

---

## Troubleshooting

### Docker not running
- **Mac**: Open Docker Desktop app
- **Check**: Run `docker ps` to verify

### AWS Authentication Failed
```bash
# Reconfigure AWS CLI
aws configure
```

### Service Not Starting
```bash
# Check App Runner logs
aws logs tail /aws/apprunner/ksdb-cloud-service --follow
```

---

## Cost Optimization

**Monthly Estimate:**
- App Runner (minimal usage): ~$10-25
- ECR Storage: ~$1
- **Total: ~$11-26/month**

**Free Tier:**
- App Runner: 2400 vCPU-minutes/month FREE
- ECR: 500 MB storage FREE for 12 months

---

## Next Steps

1. ✅ Deploy to AWS
2. ✅ Create first tenant & API key
3. ✅ Test with Python client
4. 📊 Set up monitoring (CloudWatch)
5. 🔒 Configure custom domain (Optional)
6. 💰 Set up billing alerts
