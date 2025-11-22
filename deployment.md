# KSdb AWS Deployment Guide

This guide walks you through deploying KSdb to AWS manually.

## Prerequisites
- **AWS Account**: [Create one here](https://aws.amazon.com/).
- **Docker**: Installed and running.
- **AWS CLI**:
    1.  **Install**:
        ```bash
        curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
        sudo installer -pkg AWSCLIV2.pkg -target /
        ```
    2.  **Configure**:
        Run `aws configure` and enter your:
        -   **Access Key ID**: (From IAM Console)
        -   **Secret Access Key**: (From IAM Console)
        -   **Region**: `us-east-1` (or your preferred region)
        -   **Output format**: `json`

## 1. Create Database (RDS) - **Free Tier Cheat Sheet** 📝

1.  Click this link: [Create RDS Database](https://ap-south-1.console.aws.amazon.com/rds/home?region=ap-south-1#launch-dbinstance:)
2.  **Choose a database creation method**: Select **Standard create**.
3.  **Engine options**: Select **PostgreSQL**.
4.  **Templates**: Select **Free tier** (This is the most important step!).
5.  **Settings**:
    -   **DB instance identifier**: `ksdb-postgres`
    -   **Master username**: `postgres`
    -   **Master password**: (Type a password you will remember)
6.  **Instance configuration**: Leave as `db.t3.micro` (Default).
7.  **Storage**: Leave as `20 GiB gp2` (Default).
8.  **Connectivity**:
    -   **Public access**: Select **Yes** (Easier for testing).
    -   **VPC security group**: Select **Create new**.
    -   **New VPC security group name**: `ksdb-sg`.
9.  Scroll to the bottom and click **Create database**.

**Wait**: It takes 5-10 minutes. Once "Available", copy the **Endpoint** (e.g., `ksdb-postgres.xxx.ap-south-1.rds.amazonaws.com`).

## 2. Create Storage (S3)
We need a bucket for vector indices.

1.  Go to **Amazon S3** console -> **Create bucket**.
2.  **Bucket name**: `ksdb-vectors-unique-name` (must be globally unique).
3.  **Region**: Same as your RDS (e.g., `us-east-1`).
4.  **Create bucket**.

## 3. Create Container Registry (ECR)
We need a place to store your Docker image.

1.  Go to **Amazon ECR** -> **Create repository**.
2.  **Name**: `ksdb`.
3.  **Create repository**.
4.  **Push the Image**:
    I've created a script to do this for you!
    Run in your terminal:
    ```bash
    chmod +x push_to_ecr.sh
    ./push_to_ecr.sh
    ```
    *(This builds the production image and pushes it to `701544683046.dkr.ecr.ap-south-1.amazonaws.com/ksdb`)*

## 4. Deploy Service (App Runner)
AWS App Runner is the easiest way to run the container.

1.  Go to **AWS App Runner** -> **Create service**.
2.  **Source**: Container image.
3.  **Image URI**: Click **Browse** and select `ksdb:latest` from your ECR.
4.  **Deployment settings**: Automatic.
5.  **Configuration**:
    -   **Port**: `8000`
    -   **Environment variables**:
        -   `DATABASE_URL`: (Your RDS Endpoint from Step 1)
        -   `S3_BUCKET_NAME`: `ksdb-1`
        -   `AWS_REGION`: `ap-south-1`
        -   `AWS_ACCESS_KEY_ID`: (Your Access Key)
        -   `AWS_SECRET_ACCESS_KEY`: (Your Secret Key)
6.  **Create & Deploy**.

## 6. Production Checklist 🚀

To make your app scalable and robust:

1.  **Use the Production Dockerfile**:
    Build with `docker build -f server/production.Dockerfile ...`
    This uses `gunicorn` for better concurrency.

2.  **Environment Variables**:
    -   `WORKERS`: Set to `4` (or 2x CPU cores).
    -   `TIMEOUT`: Increase to `120` if you have large uploads.
    -   `DATABASE_URL`: Ensure you use the AWS RDS endpoint.

3.  **Database (RDS)**:
    -   Upgrade from `db.t3.micro` to `db.t3.small` or larger for better performance.
    -   Enable **Multi-AZ** for high availability (if budget allows).

4.  **Scaling**:
    -   In App Runner / ECS, set **Auto Scaling** to scale up when CPU > 70%.
    -   Since indices are lazy-loaded from S3, new instances will start up fast!
