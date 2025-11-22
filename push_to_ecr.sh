#!/bin/bash
# KSdb ECR Push Script

# Configuration
REGION="ap-south-1"
ACCOUNT_ID="701544683046"
REPO_NAME="ksdb"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"

echo "--- 1. Logging in to ECR ---"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

echo "--- 2. Building Production Image ---"
# We use the production Dockerfile for optimized size and performance
docker build -t $REPO_NAME -f server/production.Dockerfile server/

echo "--- 3. Tagging Image ---"
docker tag $REPO_NAME:latest $ECR_URI:latest

echo "--- 4. Pushing to ECR ---"
docker push $ECR_URI:latest

echo "✅ Done! Image pushed to: $ECR_URI:latest"
