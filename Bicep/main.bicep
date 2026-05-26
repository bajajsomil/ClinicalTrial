targetScope = 'subscription'

@description('The Entra ID Client ID')
output entra_client_id string = entra_id.outputs.client_id

@description('The Entra ID Tenant ID')
output entra_tenant_id string = entra_id.outputs.tenant_id

@description('The Entra ID Client Secret')
output entra_client_secret string = entra_id.outputs.client_secret

@description('The Object ID of the user or Service Principal running the deployment')
param currentUserId string

@description('The Object ID of the Microsoft Graph Service Principal in your tenant')
param msgraphSpObjectId string

@description('The base name to construct names of other resources dynamically')
param baseName string = 'clinicaltrial909'

@description('The name of the resource group')
param rgName string = '${baseName}-rg'

@description('The name of the Virtual Network')
param vnetName string = '${baseName}-vnet'

@description('The name of the Azure OpenAI Service resource')
param openaiName string = '${baseName}openai'

@description('The name of the Document Intelligence resource')
param docintelName string = '${baseName}docintel'

@description('The name of the ADLS Storage Account')
param storageAccountName string = '${baseName}${substring(utcNow('yyyyMMddHHmmss'), 11, 3)}sa'

@description('The name of the Azure Container Registry')
param acrName string = '${baseName}acr'

@description('The name of the Log Analytics Workspace')
param lawName string = '${baseName}-law'

@description('The name of the Container App Environment')
param envName string = '${baseName}-env'

@description('The name of the Container App (Backend API)')
param backendAppName string = '${baseName}-capp'

@description('The name of the App Service Plan')
param aspName string = '${baseName}-asp'

@description('The name of the Frontend App Service Web App')
param frontendAppName string = '${baseName}-webapp'

@description('The Azure region for the resource group and resources')
param location string = 'switzerlandnorth'

@description('Optional: The IP address of the deployer to allow for deployment and access')
param deployerIp string = ''

@description('Optional: Additional user allowed IP address or CIDR to whitelist')
param userAllowedIp string = ''

@description('Set to true to create role assignments for Managed Identity. Set to false if you do not have User Access Administrator or Owner permissions.')
param createRoleAssignments bool = true

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: rgName
  location: location
}

module monitoring './modules/monitoring/main.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: rg.location
    lawName: lawName
  }
}

module network './modules/network/main.bicep' = {
  name: 'network'
  scope: rg
  params: {
    location: rg.location
    vnetName: vnetName
    deployerIp: deployerIp
    userAllowedIp: userAllowedIp
  }
}

module identity './modules/identity/main.bicep' = {
  name: 'identity'
  scope: rg
  params: {
    location: rg.location
    baseName: baseName
  }
}

module openai './modules/openai/main.bicep' = {
  name: 'openai'
  scope: rg
  params: {
    location: rg.location
    subnetId: network.outputs.webSubnetId
    dnsZoneId: network.outputs.dnsZoneIdOpenAI
    openaiName: openaiName
    principalId: identity.outputs.principalId
    createRoleAssignments: createRoleAssignments
    logAnalyticsWorkspaceId: monitoring.outputs.lawId
  }
}

module docintel './modules/doc_intelligence/main.bicep' = {
  name: 'docintel'
  scope: rg
  params: {
    location: rg.location
    docintelName: docintelName
    principalId: identity.outputs.principalId
    createRoleAssignments: createRoleAssignments
    subnetId: network.outputs.webSubnetId
    dnsZoneId: network.outputs.dnsZoneIdCognitive
    logAnalyticsWorkspaceId: monitoring.outputs.lawId
  }
}

module storage './modules/storage/main.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: rg.location
    storageAccountName: storageAccountName
    principalId: identity.outputs.principalId
    createRoleAssignments: createRoleAssignments
  }
}

// DEPLOY BACKEND FIRST (NO ENTRA DEP)
module app_service './modules/app_service/main.bicep' = {
  name: 'appservice'
  scope: rg
  params: {
    location: rg.location

    subnetId: network.outputs.appSubnetId
    acaEnvSubnetId: network.outputs.acaEnvSubnetId
    integrationSubnetId: network.outputs.integrationSubnetId
    dnsZoneId: network.outputs.dnsZoneIdApp

    openai_endpoint: openai.outputs.openai_endpoint
    openai_api_key: openai.outputs.openai_api_key

    docintel_endpoint: docintel.outputs.formrecognizer_endpoint
    docintel_api_key: docintel.outputs.formrecognizer_api_key

    storage_account_name: storage.outputs.storage_account_name
    storage_access_key: storage.outputs.storage_primary_access_key
    storage_connection_string: storage.outputs.storage_connection_string

    acrName: acrName
    lawName: lawName
    envName: envName
    backendAppName: backendAppName
    aspName: aspName
    frontendAppName: frontendAppName
    deployerIp: deployerIp
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
  }
}

// NOW create Entra (depends on backend URL)
module entra_id './modules/entra_id/main.bicep' = {
  name: 'entra-id-deployment-${location}'
  params: {
    currentUserId: currentUserId
    msgraphSpObjectId: msgraphSpObjectId
    backend_hostname: app_service.outputs.backend_hostname
    baseName: baseName
  }
}

// --- Outputs ---
@description('The hostname of the backend App Service')
output backend_hostname string = app_service.outputs.backend_hostname

@description('The name of the storage account')
output storage_account_name string = storage.outputs.storage_account_name

@description('The hostname of the frontend App Service')
output frontend_hostname string = app_service.outputs.frontend_hostname
