#!/bin/bash
set -e

# Check if jq is installed (Best to do this first)
if ! command -v jq &> /dev/null; then
    echo "Error: 'jq' is not installed. Please install it (e.g., 'apt-get install jq' or 'brew install jq')."
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
    echo "Using custom base name from argument: $BASE_NAME"
else
    # Interactive prompt with timeout for premium developer experience
    echo -n "Enter custom base name for resources [default: $DEFAULT_BASE_NAME] (timeout 20s): "
    if read -t 20 input_val; then
        BASE_NAME="$input_val"
    fi
    if [ -z "$BASE_NAME" ]; then
        BASE_NAME="$DEFAULT_BASE_NAME"
        echo -e "\nTimeout or empty input. Using default: $BASE_NAME"
    else
        echo "Using custom base name: $BASE_NAME"
    fi
fi

# Check command line argument for location second
if [ ! -z "$2" ]; then
    LOCATION="$2"
    echo "Using custom region from argument: $LOCATION"
else
    # Interactive prompt with timeout for premium developer experience
    echo -n "Enter Azure region for deployment [default: $DEFAULT_LOCATION] (timeout 20s): "
    if read -t 20 input_loc; then
        LOCATION="$input_loc"
    fi
    if [ -z "$LOCATION" ]; then
        LOCATION="$DEFAULT_LOCATION"
        echo -e "\nTimeout or empty input. Using default: $LOCATION"
    else
        echo "Using region: $LOCATION"
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

# Calculate deterministic 3-digit suffix for storage account
BASE_HASH=$(echo -n "$BASE_NAME" | cksum | cut -d' ' -f1)
STORAGE_SUFFIX=$(echo "${BASE_HASH:0:3}")
STORAGE_ACCOUNT_NAME=$(echo "${BASE_NAME}${STORAGE_SUFFIX}sa" | tr -d '\r')

IMAGE_NAME="backend-api"
IMAGE_TAG=$(date +%s | tr -d '\r')

echo "================================================="
echo "Starting Clinical Deployment (Bicep + ACA)"
echo "   Base Name:     $BASE_NAME"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   ACR Name:      $ACR_NAME"
echo "   API (ACA):     $ACA_NAME"
echo "   UI App Service: $UI_NAME"
echo "   Region/Location: $LOCATION"
echo "================================================="

echo "Deploying Infrastructure..."

ACCOUNT_TYPE=$(az account show --query user.type -o tsv | tr -d '\r')
ACCOUNT_NAME=$(az account show --query user.name -o tsv | tr -d '\r')

if [ "$ACCOUNT_TYPE" == "user" ]; then
    CURRENT_USER_ID=$(az ad signed-in-user show --query id -o tsv | tr -d '\r')
else
    CURRENT_USER_ID=$(az ad sp show --id "$ACCOUNT_NAME" --query id -o tsv | tr -d '\r')
fi

# Fixed double quote issue for SP query
MSGRAPH_SP_ID=$(az ad sp list --display-name "Microsoft Graph" --query "[0].id" -o tsv | tr -d '\r')

# Fetch deployer's public IP
echo "Fetching deployer public IP..."
DEPLOYER_IP=$(curl -s https://api.ipify.org | tr -d '\r')
if [ -z "$DEPLOYER_IP" ]; then
    DEPLOYER_IP=$(curl -s https://ifconfig.me | tr -d '\r')
fi
if [ -z "$DEPLOYER_IP" ]; then
    echo "Warning: Failed to fetch deployer public IP. App Service deployment might fail if public access is restricted."
else
    echo "Deployer Public IP: $DEPLOYER_IP"
fi

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
    storageAccountName="$STORAGE_ACCOUNT_NAME" \
    location="$LOCATION" \
    deployerIp="$DEPLOYER_IP" \
  --output json | tr -d '\r')


BACKEND_HOST=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.backend_hostname.value')
FRONTEND_HOST=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.frontend_hostname.value')
STORAGE_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.storage_account_name.value')
ENTRA_CLIENT_ID=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.entra_client_id.value')
ENTRA_TENANT_ID=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.entra_tenant_id.value')
ENTRA_CLIENT_SECRET=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.entra_client_secret.value')

if [ "$ENTRA_CLIENT_SECRET" == "placeholder" ] && [ ! -z "$ENTRA_CLIENT_ID" ] && [ "$ENTRA_CLIENT_ID" != "null" ]; then
    echo "Generating real Entra ID Client Secret dynamically via service actions..."
    # Wrap in || true to prevent script from crashing if command fails
    ENTRA_CLIENT_SECRET=$(az ad app credential reset --id "$ENTRA_CLIENT_ID" --append --display-name "ClinicalAppSecret" --query password -o tsv 2>/dev/null | tr -d '\r') || true
fi

# Ensure Entra variables are not empty or null to avoid deployment crashes
if [ -z "$ENTRA_CLIENT_SECRET" ] || [ "$ENTRA_CLIENT_SECRET" == "null" ]; then
    echo "Warning: Entra ID Client Secret is empty or null. Using placeholder."
    ENTRA_CLIENT_SECRET="placeholder-secret-value"
fi

if [ -z "$ENTRA_CLIENT_ID" ] || [ "$ENTRA_CLIENT_ID" == "null" ]; then
    ENTRA_CLIENT_ID="placeholder-client-id"
fi

if [ -z "$ENTRA_TENANT_ID" ] || [ "$ENTRA_TENANT_ID" == "null" ]; then
    ENTRA_TENANT_ID="placeholder-tenant-id"
fi

echo "Backend Host: $BACKEND_HOST"

# # --- Dynamic Scaling for Azure OpenAI Model Deployments ---
# scale_deployment_to_max() {
#     local dep_name=$1
#     local max_cap=100
#     local openai_account_name="${BASE_NAME}openai"

#     # 1. Fetch deployment information to get SKU and Model details
#     local dep_info
#     dep_info=$(az cognitiveservices account deployment show \
#       --resource-group "$RESOURCE_GROUP" \
#       --name "$openai_account_name" \
#       --deployment-name "$dep_name" \
#       --output json 2>/dev/null)

#     if [ -z "$dep_info" ]; then
#         echo "   Warning: Could not find deployment info for '$dep_name'. Skipping dynamic scaling."
#         return 0
#     fi

#     local sku_name
#     sku_name=$(echo "$dep_info" | jq -r '.sku.name')
#     local model_name
#     model_name=$(echo "$dep_info" | jq -r '.properties.model.name')
#     local current_cap
#     current_cap=$(echo "$dep_info" | jq -r '.sku.capacity')

#     # 2. Determine target capacity based on remaining available quota
#     local target_cap=$max_cap

#     if [ -n "$USAGES_JSON" ] && [ "$USAGES_JSON" != "[]" ]; then
#         # Construct quota key: e.g., OpenAI.GlobalStandard.gpt-4o or OpenAI.Standard.gpt-4o
#         local quota_key="OpenAI.${sku_name}.${model_name}"
#         local quota_item
#         quota_item=$(echo "$USAGES_JSON" | jq --arg key "$quota_key" '.[] | select(.name.value == $key)')

#         if [ -n "$quota_item" ]; then
#             local limit
#             limit=$(echo "$quota_item" | jq -r '.limit')
#             local currentValue
#             currentValue=$(echo "$quota_item" | jq -r '.currentValue')

#             # Calculate remaining quota safely using jq (handles decimals/floats gracefully)
#             local remaining_quota
#             remaining_quota=$(jq -n --arg limit "$limit" --arg cur "$currentValue" '($limit | tonumber) - ($cur | tonumber) | floor')

#             # Standard SKU limit is in TPM (e.g. 100000), need to convert to Thousands (k) TPM
#             local remaining_quota_k
#             if [ "$sku_name" == "Standard" ]; then
#                 remaining_quota_k=$(jq -n --arg rem "$remaining_quota" '($rem | tonumber) / 1000 | floor')
#             else
#                 remaining_quota_k=$remaining_quota
#             fi

#             # Add current deployment capacity back (since it is already counted in currentValue)
#             # and limit target to max_cap
#             target_cap=$(jq -n --arg max "$max_cap" --arg rem "$remaining_quota_k" --arg cur "$current_cap" '
#               [($max | tonumber), (($rem | tonumber) + ($cur | tonumber))] | min | floor
#             ')
#         else
#             echo "   Quota item '$quota_key' not found in regional usage list. Using default maximum."
#         fi
#     fi

#     if [ "$target_cap" -lt 1 ]; then
#         target_cap=1
#     fi

#     echo "Scaling '$dep_name' ($sku_name $model_name) to target capacity of ${target_cap}k TPM..."

#     # 3. Perform a single update call with transparent error capture
#     local update_err
#     update_err=$(az resource update \
#       --resource-group "$RESOURCE_GROUP" \
#       --resource-type "Microsoft.CognitiveServices/accounts/deployments" \
#       --parent "accounts/$openai_account_name" \
#       --name "$dep_name" \
#       --set sku.capacity="$target_cap" \
#       --query "sku.capacity" -o tsv 2>&1)

#     if [ $? -eq 0 ]; then
#         echo "   Successfully scaled '$dep_name' to ${target_cap}k TPM!"
#         return 0
#     else
#         echo "   Failed to scale to ${target_cap}k TPM. Error: $update_err"
#         if [ "$target_cap" -gt 1 ]; then
#             echo "   Falling back to safe capacity of 1k TPM..."
#             if az resource update \
#               --resource-group "$RESOURCE_GROUP" \
#               --resource-type "Microsoft.CognitiveServices/accounts/deployments" \
#               --parent "accounts/$openai_account_name" \
#               --name "$dep_name" \
#               --set sku.capacity=1 \
#               --query "sku.capacity" -o tsv >/dev/null 2>&1; then
#                 echo "   Successfully scaled '$dep_name' to 1k TPM!"
#                 return 0
#             else
#                 echo "   Warning: Could not scale '$dep_name' beyond Bicep default capacity."
#             fi
#         fi
#     fi
# }

# echo -e "\nScaling OpenAI Model Capacities..."
# # Query regional Cognitive Services usages once to prevent ARM rate limits (429)
# USAGES_JSON=$(az cognitiveservices usage list --location "$LOCATION" --output json 2>/dev/null || echo "[]")

# scale_deployment_to_max "gpt41"
# scale_deployment_to_max "gpt41_mini"
# scale_deployment_to_max "gpt4o"
# scale_deployment_to_max "gpt4o_mini"

echo -e "\nBuilding & Pushing Docker Image..."

cd ../backend

az acr login --name $ACR_NAME

ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv | tr -d '\r')
FULL_IMAGE_NAME="$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"

docker build -t $FULL_IMAGE_NAME .
docker push $FULL_IMAGE_NAME

echo -e "\nUpdating Container App..."

az containerapp update \
  --name $ACA_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $FULL_IMAGE_NAME \
  --set-env-vars \
    BACKEND_URL="https://${BACKEND_HOST}" \
    FRONTEND_URL="https://${FRONTEND_HOST}"

echo "Injecting Entra into Container App..."

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

echo "Applying CORS..."
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
VITE_PHARMA_CONTAINER_URL=https://${STORAGE_NAME}.blob.core.windows.net/pharma
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

# Access Security Configuration
echo -e "\nAccess Security Configuration:"
echo -n "Do you want to whitelist an IP address/CIDR block on the Frontend App Service? (y/n) [default: n]: "
read -r whitelist_choice
if [[ "$whitelist_choice" =~ ^[Yy]$ ]]; then
    echo -n "Enter the IP address or CIDR range to whitelist (e.g. 192.168.1.0/24 or 203.0.113.5/32): "
    read -r whitelist_ip
    if [ ! -z "$whitelist_ip" ]; then
        echo "Whitelisting $whitelist_ip on Frontend App Service $UI_NAME..."
        az webapp config access-restriction add \
          --resource-group "$RESOURCE_GROUP" \
          --name "$UI_NAME" \
          --rule-name "UserWhitelistedIp" \
          --action Allow \
          --ip-address "$whitelist_ip" \
          --priority 200 \
          --description "Allow access from user whitelisted IP address space"
        echo "Whitelisted successfully!"
    else
        echo "Warning: No IP address provided. Skipping whitelisting."
    fi
else
    echo "Skipping IP whitelisting."
fi

echo "================================================="
echo "Deployment Complete!"
echo "   Frontend: https://${FRONTEND_HOST}"
echo "   Backend: https://${BACKEND_HOST}"
echo "================================================="