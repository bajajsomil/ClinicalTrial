#!/bin/bash
set -e

# Check if jq is installed (Best to do this first)
if ! command -v jq &> /dev/null; then
    echo "❌ Error: 'jq' is not installed. Please install it (e.g., 'apt-get install jq' or 'brew install jq')."
    exit 1
fi

# Default base name
DEFAULT_BASE_NAME="clinicaltrial909"
DEFAULT_BASE_NAME=$(echo "$DEFAULT_BASE_NAME" | tr -d '\r')
BASE_NAME=""

# Default region/location
DEFAULT_LOCATION="switzerlandnorth"
DEFAULT_LOCATION=$(echo "$DEFAULT_LOCATION" | tr -d '\r')
LOCATION=""

# Check command line argument for base name first
if [ ! -z "$1" ]; then
    BASE_NAME="$1"
    echo "🎯 Using custom base name from argument: $BASE_NAME"
else
    # Interactive prompt with timeout for premium developer experience
    echo -n "❓ Enter custom base name for resources [default: $DEFAULT_BASE_NAME] (timeout 10s): "
    if read -t 10 input_val; then
        BASE_NAME="$input_val"
    fi
    if [ -z "$BASE_NAME" ]; then
        BASE_NAME="$DEFAULT_BASE_NAME"
        echo -e "\n⏰ Timeout or empty input. Using default: $BASE_NAME"
    else
        echo "🎯 Using custom base name: $BASE_NAME"
    fi
fi

# Check command line argument for location second
if [ ! -z "$2" ]; then
    LOCATION="$2"
    echo "🎯 Using custom region from argument: $LOCATION"
else
    # Interactive prompt with timeout for premium developer experience
    echo -n "❓ Enter Azure region for deployment [default: $DEFAULT_LOCATION] (timeout 10s): "
    if read -t 10 input_loc; then
        LOCATION="$input_loc"
    fi
    if [ -z "$LOCATION" ]; then
        LOCATION="$DEFAULT_LOCATION"
        echo -e "\n⏰ Timeout or empty input. Using default: $LOCATION"
    else
        echo "🎯 Using region: $LOCATION"
    fi
fi

# Clean carriage returns from any input or script line endings
BASE_NAME=$(echo "$BASE_NAME" | tr -d '\r')
LOCATION=$(echo "$LOCATION" | tr -d '\r')

# Sanitize and construct dynamic names
RESOURCE_GROUP=$(echo "${BASE_NAME}-rg" | tr -d '\r')
# ACR name must be strictly lowercase, alphanumeric, 5-50 characters
ACR_NAME=$(echo "${BASE_NAME}acr" | tr -d '-' | tr -d '_' | tr '[:upper:]' '[:lower:]' | cut -c 1-50 | tr -d '\r')
ACA_NAME=$(echo "${BASE_NAME}-api" | tr -d '\r')
UI_NAME=$(echo "${BASE_NAME}-ui" | tr -d '\r')

IMAGE_NAME="backend-api"
IMAGE_TAG=$(date +%s | tr -d '\r')

echo "================================================="
echo "🚀 Starting Clinical Deployment (Bicep + ACA)"
echo "   Base Name:     $BASE_NAME"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   ACR Name:      $ACR_NAME"
echo "   API (ACA):     $ACA_NAME"
echo "   UI App Service: $UI_NAME"
echo "   Region/Location: $LOCATION"
echo "================================================="

echo "🏗️ Deploying Infrastructure..."

ACCOUNT_TYPE=$(az account show --query user.type -o tsv | tr -d '\r')
ACCOUNT_NAME=$(az account show --query user.name -o tsv | tr -d '\r')

if [ "$ACCOUNT_TYPE" == "user" ]; then
    CURRENT_USER_ID=$(az ad signed-in-user show --query id -o tsv | tr -d '\r')
else
    CURRENT_USER_ID=$(az ad sp show --id "$ACCOUNT_NAME" --query id -o tsv | tr -d '\r')
fi

# Fixed double quote issue for SP query
MSGRAPH_SP_ID=$(az ad sp list --display-name "Microsoft Graph" --query "[0].id" -o tsv | tr -d '\r')

DEPLOY_NAME="clinical-trial-deployment-$(date +%s)"

# Run Deployment with dynamic parameters
DEPLOYMENT_OUTPUT=$(az deployment sub create \
  --name "$DEPLOY_NAME" \
  --location "$LOCATION" \
  --template-file main.bicep \
  --parameters \
    currentUserId="$CURRENT_USER_ID" \
    msgraphSpObjectId="$MSGRAPH_SP_ID" \
    baseName="$BASE_NAME" \
    rgName="$RESOURCE_GROUP" \
    acrName="$ACR_NAME" \
    backendAppName="$ACA_NAME" \
    frontendAppName="$UI_NAME" \
    location="$LOCATION" \
  --output json | tr -d '\r')


BACKEND_HOST=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.backend_hostname.value')
FRONTEND_HOST=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.frontend_hostname.value')
STORAGE_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.storage_account_name.value')
ENTRA_CLIENT_ID=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.entra_client_id.value')
ENTRA_TENANT_ID=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.entra_tenant_id.value')
ENTRA_CLIENT_SECRET=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.entra_client_secret.value')

if [ "$ENTRA_CLIENT_SECRET" == "placeholder" ]; then
    echo "🔑 Generating real Entra ID Client Secret dynamically via service actions..."
    ENTRA_CLIENT_SECRET=$(az ad app credential reset --id "$ENTRA_CLIENT_ID" --append --display-name "ClinicalAppSecret" --query password -o tsv | tr -d '\r')
fi

echo "✅ Backend Host: $BACKEND_HOST"

echo -e "\n🐳 Building & Pushing Docker Image..."

cd ../backend

az acr login --name $ACR_NAME

ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv | tr -d '\r')
FULL_IMAGE_NAME="$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"

docker build -t $FULL_IMAGE_NAME .
docker push $FULL_IMAGE_NAME

echo -e "\n🚀 Updating Container App..."

az containerapp update \
  --name $ACA_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $FULL_IMAGE_NAME \
  --set-env-vars \
    BACKEND_URL="https://${BACKEND_HOST}" \
    FRONTEND_URL="https://${FRONTEND_HOST}"

echo "🔐 Injecting Entra into Container App..."

az containerapp secret set \
  --name $ACA_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets "azure-client-secret=$ENTRA_CLIENT_SECRET"

az containerapp update \
  --name $ACA_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    ENTRA_CLIENT_ID="$ENTRA_CLIENT_ID" \
    ENTRA_TENANT_ID="$ENTRA_TENANT_ID"

echo "🛡️ Applying CORS..."
az containerapp ingress cors update \
  --name $ACA_NAME \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "https://${FRONTEND_HOST}" "http://localhost:5173" \
  --allowed-methods "*" \
  --allowed-headers "*"

cd ../frontend

cat <<EOF > .env
VITE_BACKEND_URL=https://${BACKEND_HOST}
VITE_BLOB_STORAGE_URL=https://${STORAGE_NAME}.blob.core.windows.net
EOF

npm install --quiet
npm run build --quiet

cd dist
zip -r ../frontend.zip .

az webapp deploy \
  --resource-group $RESOURCE_GROUP \
  --name $UI_NAME \
  --src-path ../frontend.zip \
  --type zip

echo "================================================="
echo "🎉 Deployment Complete!"
echo "🌐 Frontend: https://${FRONTEND_HOST}"
echo "⚙️ Backend: https://${BACKEND_HOST}"
echo "================================================="