#!/bin/bash
# ============================================================
# deploy.sh — Build, push to ECR, update ECS service
# Usage: ./deploy.sh <region> <account-id> <rds-endpoint> [image-tag]
# Example: ./deploy.sh us-east-1 123456789012 mydb.abc123.us-east-1.rds.amazonaws.com v1.2
# ============================================================
set -e

REGION="${1:?Usage: ./deploy.sh <region> <account-id> <rds-endpoint> [image-tag]}"
ACCOUNT_ID="${2:?Usage: ./deploy.sh <region> <account-id> <rds-endpoint> [image-tag]}"
RDS_ENDPOINT="${3:?Usage: ./deploy.sh <region> <account-id> <rds-endpoint> [image-tag]}"
IMAGE_TAG="${4:-v2.0.0-Mizunoe}"

REPO_NAME="reconroll-backend"
NGINX_REPO_NAME="reconroll-nginx"
CLUSTER_NAME="reconroll-cluster"
SERVICE_NAME="reconroll-service"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"
NGINX_ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${NGINX_REPO_NAME}"

echo "==> [1/5] Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> [2/5] Creating ECR repos if they don't exist..."
aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" > /dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$REPO_NAME" --region "$REGION" > /dev/null
aws ecr describe-repositories --repository-names "$NGINX_REPO_NAME" --region "$REGION" > /dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$NGINX_REPO_NAME" --region "$REGION" > /dev/null

echo "==> [3/5] Building images with code baked in..."
# Build from the backend/ directory so COPY ./app and COPY ./scripts work
docker build \
  --build-arg VIDEO_GID=44 \
  -t "${REPO_NAME}:${IMAGE_TAG}" \
  -f Dockerfile \
  .

docker build \
  -t "${NGINX_REPO_NAME}:${IMAGE_TAG}" \
  -f nginx/Dockerfile \
  ./nginx

echo "==> [4/5] Tagging and pushing to ECR..."
docker tag "${REPO_NAME}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"

docker tag "${NGINX_REPO_NAME}:${IMAGE_TAG}" "${NGINX_ECR_URI}:${IMAGE_TAG}"
docker push "${NGINX_ECR_URI}:${IMAGE_TAG}"

echo "==> [5/5] Registering task definition and deploying..."
TASK_DEF_FILE=$(mktemp /tmp/ecs-task-def-XXXXXX.json)
trap "rm -f $TASK_DEF_FILE" EXIT

sed \
  -e "s|<ACCOUNT_ID>|${ACCOUNT_ID}|g" \
  -e "s|<REGION>|${REGION}|g" \
  -e "s|<RDS_ENDPOINT>|${RDS_ENDPOINT}|g" \
  ecs-task-definition.json > "$TASK_DEF_FILE"

NEW_TASK_ARN=$(aws ecs register-task-definition \
  --region "$REGION" \
  --cli-input-json "file://${TASK_DEF_FILE}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "    New task definition: $NEW_TASK_ARN"

aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --task-definition "$NEW_TASK_ARN" \
  --force-new-deployment \
  --region "$REGION" \
  --output text --query 'service.serviceName'

echo ""
echo "Done. Rolling deployment started on ${CLUSTER_NAME}/${SERVICE_NAME}"
echo "Watch progress: aws ecs wait services-stable --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${REGION}"
