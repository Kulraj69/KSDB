# KSdb Cloud Deployment Guide

## Overview

Deploy KSdb as a managed cloud service like ChromaDB Cloud, with:
- ✅ API Key authentication
- ✅ Multi-tenant isolation
- ✅ Production PostgreSQL database
- ✅ Auto-scaling on AWS App Runner
- ✅ HTTPS with automatic certificates

---

## Prerequisites

1. **AWS Account** with CLI configured
2. **Docker** installed locally
3. **Environment Variables**:
   ```bash
   export AWS_REGION="us-east-1"
   export DATABASE_URL="postgresql://user:pass@host:5432/ksdb"
   export ADMIN_KEY="your-secure-admin-key-here"
   ```

---

## Quick Deploy (5 minutes)

### Option 1: AWS App Runner (Recommended)

```bash
# 1. Make deploy script executable
chmod +x deploy/deploy_aws.sh

# 2. Set environment variables
export DATABASE_URL="postgresql://..."  # Your RDS connection string
export ADMIN_KEY="$(openssl rand -hex 32)"  # Generate secure key

# 3. Deploy!
./deploy/deploy_aws.sh
```

**That's it!** The script will:
- Build Docker image
- Push to AWS ECR
- Create/update App Runner service
- Output your API URL

### Option 2: Docker Compose (Local Testing)

```bash
# 1. Create .env file
cat > .env << EOF
DB_PASSWORD=$(openssl rand -hex 16)
ADMIN_KEY=$(openssl rand -hex 32)
EOF

# 2. Start services
docker-compose -f docker-compose.cloud.yml up -d

# 3. Check health
curl http://localhost:8000/health
```

---

## Post-Deployment Setup

### 1. Create Your First Tenant

```bash
# Replace with your deployed URL
export KSDB_URL="https://your-app.us-east-1.awsapprunner.com"

# Create tenant (save the API key!)
curl -X POST "$KSDB_URL/admin/create-tenant?tenant_name=my-company&admin_key=$ADMIN_KEY"

# Response:
# {
#   "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
#   "api_key": "ks_live_abc123...",
#   "message": "Save this API key securely. It cannot be retrieved later."
# }
```

**⚠️ Important**: Save the `api_key` immediately. It cannot be retrieved later!

### 2. Test with Python SDK

```python
from ksdb import CloudClient

# Connect to your KSdb Cloud
client = CloudClient(
    api_key="ks_live_abc123...",  # From step 1
    url="https://your-app.us-east-1.awsapprunner.com"
)

# Create collection
collection = client.get_or_create_collection("my_docs")

# Add documents (with auto-dedup and graph extraction)
collection.add(
    ids=["doc1", "doc2"],
    documents=[
        "KSdb is a fast vector database",
        "It supports hybrid search"
    ],
    deduplicate=True,
    extract_graph=True
)

# Search
results = collection.query(
    query_texts=["What is KSdb?"],
    n_results=5
)

print(results)
```

### 3. Manage API Keys

```python
# List all keys
keys = client._request("GET", "/auth/keys")

# Create additional key
new_key = client._request("POST", "/auth/keys", json={"name": "production-key"})

# Revoke key
client._request("DELETE", f"/auth/keys/{key_to_revoke}")
```

---

## Production Configuration

### Database (PostgreSQL RDS)

**Recommended Setup:**
- Instance: `db.t3.micro` (free tier) or `db.t3.small`
- Storage: 20GB SSD
- Backups: Automated daily
- Multi-AZ: Enabled for production

```bash
# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier ksdb-postgres \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username ksdb \
    --master-user-password "$(openssl rand -hex 16)" \
    --allocated-storage 20 \
    --publicly-accessible

# Get connection string
aws rds describe-db-instances \
    --db-instance-identifier ksdb-postgres \
    --query 'DBInstances[0].Endpoint.Address'
```

### App Runner Configuration

**Auto-Scaling:**
- Min instances: 1
- Max instances: 10
- CPU: 1 vCPU
- Memory: 2 GB

**Environment Variables:**
```bash
DATABASE_URL=postgresql://ksdb:password@endpoint.rds.amazonaws.com:5432/ksdb
ADMIN_KEY=your-secure-admin-key
EMBEDDING_MODEL=all-MiniLM-L6-v2
INDEX_PATH=/data/indices
```

---

## Security Best Practices

### 1. API Key Management

```python
# Client-side: Store API keys securely
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("KSDB_API_KEY")  # Never hardcode!

client = CloudClient(api_key=api_key, url=os.getenv("KSDB_URL"))
```

### 2. Rate Limiting (Optional)

Add to `cloud_server.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/collections/{name}/add")
@limiter.limit("100/minute")  # Limit to 100 requests per minute
async def add_documents(...):
    ...
```

### 3. CORS Configuration

Update `cloud_server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],  # Restrict to your domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

---

## Monitoring & Observability

### Health Checks

```bash
# Service health
curl https://your-app.awsapprunner.com/health

# Response:
# {"status": "healthy", "service": "ksdb-cloud"}
```

### CloudWatch Metrics

```bash
# View App Runner metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/AppRunner \
    --metric-name RequestCount \
    --dimensions Name=ServiceName,Value=ksdb-cloud-service \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum
```

### Logging

```bash
# View logs
aws logs tail /aws/apprunner/ksdb-cloud-service --follow
```

---

## Pricing Estimate

### AWS Costs (Monthly)

| Service | Configuration | Cost |
|---------|--------------|------|
| **App Runner** | 1 vCPU, 2GB RAM | ~$25 |
| **RDS (PostgreSQL)** | db.t3.micro | ~$15 (free tier eligible) |
| **ECR** | Image storage | ~$1 |
| **Data Transfer** | 100GB | ~$9 |
| **Total** | | **~$50/month** |

### Cost Optimization

1. **Use free tier**: RDS t3.micro is free for 12 months
2. **Auto-pause App Runner**: Set min instances to 0 for dev environments
3. **Optimize images**: Use multi-stage Docker builds

---

## Troubleshooting

### Common Issues

**1. API Key Invalid**
```python
# Verify key format
assert api_key.startswith("ks_live_"), "Invalid API key format"
```

**2. Database Connection Failed**
```bash
# Test RDS connection
psql "$DATABASE_URL"
```

**3. Service Not Starting**
```bash
# Check App Runner logs
aws logs tail /aws/apprunner/ksdb-cloud-service --since 1h
```

---

## Updating Your Deployment

```bash
# Make code changes, then:
./deploy/deploy_aws.sh  # Automatically builds and deploys

# Or manual update:
docker build -f Dockerfile.cloud -t ksdb-cloud:latest .
docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/ksdb-cloud:latest
```

---

## Next Steps

1. **Set up custom domain**: 
   - Configure Route 53
   - Add custom domain to App Runner

2. **Enable HTTPS**: App Runner provides automatic TLS certificates

3. **Monitor usage**:
   - Set up CloudWatch alarms
   - Track API usage per tenant

4. **Scale up**:
   - Increase App Runner instances
   - Upgrade RDS instance size

---

## Support

- **Issues**: https://github.com/Kulraj69/KSDB/issues
- **Discussions**: https://github.com/Kulraj69/KSDB/discussions
- **Email**: support@ksdb.dev (if you set up a domain)
