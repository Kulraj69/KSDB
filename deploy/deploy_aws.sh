#!/bin/bash

# KSdb Cloud - AWS Deployment Script
# This script deploys KSdb to AWS App Runner

set -e

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
ECR_REPO_NAME="ksdb-cloud"
APP_NAME="ksdb-cloud"
SERVICE_NAME="ksdb-cloud-service"

echo "🚀 Deploying KSdb Cloud to AWS..."

# 1. Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $AWS_REGION

# Get ECR login
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

# 2. Build Docker image
echo "🏗️  Building Docker image..."
docker build -f Dockerfile.cloud -t $ECR_REPO_NAME:latest .

# 3. Tag and push to ECR
echo "📤 Pushing to ECR..."
ECR_URI=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest

echo "✅ Image pushed to: $ECR_URI:latest"

# 4. Create App Runner service (or update if exists)
echo "🌐 Deploying to App Runner..."

# Check if service exists
SERVICE_ARN=$(aws apprunner list-services --region $AWS_REGION --query "ServiceSummaryList[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text)

if [ -z "$SERVICE_ARN" ]; then
    echo "Creating new App Runner service..."
    
    # Create service
    aws apprunner create-service \
        --service-name $SERVICE_NAME \
        --region $AWS_REGION \
        --source-configuration "{
            \"ImageRepository\": {
                \"ImageIdentifier\": \"$ECR_URI:latest\",
                \"ImageRepositoryType\": \"ECR\",
                \"ImageConfiguration\": {
                    \"Port\": \"8000\",
                    \"RuntimeEnvironmentVariables\": {
                        \"DATABASE_URL\": \"$DATABASE_URL\",
                        \"ADMIN_KEY\": \"$ADMIN_KEY\"
                    }
                }
            },
            \"AutoDeploymentsEnabled\": true
        }" \
        --instance-configuration "{
            \"Cpu\": \"1 vCPU\",
            \"Memory\": \"2 GB\"
        }" \
        --health-check-configuration "{
            \"Protocol\": \"HTTP\",
            \"Path\": \"/health\",
            \"Interval\": 10,
            \"Timeout\": 5,
            \"HealthyThreshold\": 1,
            \"UnhealthyThreshold\": 5
        }"
    
    echo "✅ App Runner service created!"
else
    echo "Updating existing App Runner service..."
    
    # Update service
    aws apprunner update-service \
        --service-arn $SERVICE_ARN \
        --region $AWS_REGION \
        --source-configuration "{
            \"ImageRepository\": {
                \"ImageIdentifier\": \"$ECR_URI:latest\",
                \"ImageRepositoryType\": \"ECR\"
            }
        }"
    
    echo "✅ App Runner service updated!"
fi

# Wait for service to be ready
echo "⏳ Waiting for service to be ready..."
aws apprunner wait service-ready --service-arn $SERVICE_ARN --region $AWS_REGION

# Get service URL
SERVICE_URL=$(aws apprunner describe-service --service-arn $SERVICE_ARN --region $AWS_REGION --query "Service.ServiceUrl" --output text)

echo ""
echo "════════════════════════════════════════════════"
echo "✅ Deployment Complete!"
echo "════════════════════════════════════════════════"
echo "🌐 Service URL: https://$SERVICE_URL"
echo "📚 API Docs: https://$SERVICE_URL/docs"
echo ""
echo "Next steps:"
echo "1. Create your first tenant:"
echo "   curl -X POST \"https://$SERVICE_URL/admin/create-tenant?tenant_name=my-org&admin_key=YOUR_ADMIN_KEY\""
echo ""
echo "2. Use the returned API key with the SDK:"
echo "   from ksdb import CloudClient"
echo "   client = CloudClient(api_key=\"ks_live_...

\", url=\"https://$SERVICE_URL\")"
echo "════════════════════════════════════════════════"
