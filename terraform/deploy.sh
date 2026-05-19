#!/bin/bash
set -e

# === Configuration Variables ===
RESOURCE_GROUP="clinical-trial123654"
ACR_NAME="clinicaltrialacr123654"
ACA_NAME="clinical-trial-api123654"
UI_NAME="clinical-trial-ui123654"
IMAGE_NAME="backend-api"
IMAGE_TAG=$(date +%s)

echo "================================================="
echo "🚀 Starting Clinical Deployment (Env 13)"
echo "================================================="

# [1-5] Terraform Sequence
terraform init -upgrade
terraform fmt
terraform validate
terraform plan -out=tfplan
terraform apply -auto-approve "tfplan"

# --- Fetch Outputs ---
FRONTEND_HOST=$(terraform output -raw frontend_hostname -no-color 2>/dev/null | tail -n 1 | tr -d '\r')
RAW_BACKEND_HOST=$(terraform output -raw backend_hostname -no-color 2>/dev/null | tail -n 1 | tr -d '\r')
STORAGE_NAME=$(terraform output -raw storage_account_name -no-color 2>/dev/null | tail -n 1 | tr -d '\r')
ENTRA_CLIENT_ID=$(terraform output -raw entra_client_id -no-color 2>/dev/null | tail -n 1 | tr -d '\r')
CONTAINER_NAME="pharma"

echo "🧐 VERIFYING: Backend Host is '$RAW_BACKEND_HOST'"

# --- 🎯 THE FIX: Dynamically update Entra ID Redirect URIs ---
echo "🔐 Updating Entra ID App Registration with Production Callback URL..."
az ad app update \
  --id "$ENTRA_CLIENT_ID" \
  --web-redirect-uris "http://localhost:8000/callback" "https://${RAW_BACKEND_HOST}/callback"

echo -e "\n[6/7] Packaging and Deploying Backend (Docker -> ACR -> ACA)..."
cd ../backend || exit 1

echo "🔑 Logging into Azure Container Registry..."
az acr login --name $ACR_NAME

ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
FULL_IMAGE_NAME="$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"

echo "🐳 Building Docker Image..."
docker build -t $FULL_IMAGE_NAME .

echo "☁️ Pushing Docker Image to ACR..."
docker push $FULL_IMAGE_NAME

# --- 🎯 THE FIX: Inject missing Environment Variables ---
echo "🔄 Updating Azure Container App with new image & ENV vars..."
az containerapp update \
  --name $ACA_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $FULL_IMAGE_NAME \
  --set-env-vars BACKEND_URL="https://${RAW_BACKEND_HOST}" FRONTEND_URL="https://${FRONTEND_HOST}"

# Apply CORS
echo "🛡️ Configuring CORS Policy for $FRONTEND_HOST..."
az containerapp ingress cors update \
  --name $ACA_NAME \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "https://${FRONTEND_HOST}" "http://localhost:5173" "http://localhost:3000" \
  --allowed-methods "*" \
  --allowed-headers "*" \
  --expose-headers "*"

cd ../terraform

echo -e "\n[7/7] Packaging and Deploying Frontend (Node/React)..."
cd ../frontend || exit 1

echo "📝 Writing .env and building locally..."
cat <<EOF > .env
VITE_BACKEND_URL=https://${RAW_BACKEND_HOST}
VITE_BLOB_STORAGE_URL=https://${STORAGE_NAME}.blob.core.windows.net
VITE_PHARMA_CONTAINER_URL=https://${STORAGE_NAME}.blob.core.windows.net/${CONTAINER_NAME}
EOF

npm install --quiet
npm run build --quiet

cd dist || exit 1

echo "📦 Zipping and Deploying frontend..."
zip -r ../frontend_deploy.zip .

az webapp deploy \
  --resource-group $RESOURCE_GROUP \
  --name $UI_NAME \
  --src-path ../frontend_deploy.zip \
  --type zip

rm ../frontend_deploy.zip

cd ../../terraform

echo "🎉 Deployment Complete!"
echo "🔗 You can visit your app at: https://${FRONTEND_HOST}/home"