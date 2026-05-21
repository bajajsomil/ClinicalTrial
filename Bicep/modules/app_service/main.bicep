@description('Location for all resources.')
param location string = resourceGroup().location

@description('Optional: Subnet ID to deploy a private endpoint for the Frontend App Service')
param subnetId string = ''

@description('Optional: Subnet ID to deploy the VNet integration for the Frontend App Service')
param integrationSubnetId string = ''

@description('Optional: Subnet ID to deploy the Azure Container Apps Environment')
param acaEnvSubnetId string = ''

@description('Optional: Private DNS Zone ID for the App Service')
param dnsZoneId string = ''

@description('Public network access status for the Frontend App Service')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Disabled'

@description('Optional: The IP address of the deployer to allow for deployment and access')
param deployerIp string = ''

@description('The name of the Azure Container Registry')
param acrName string = 'clinicaltrialacr909'

@description('The name of the Log Analytics Workspace')
param lawName string = 'clinical-trial-log909'

@description('The name of the Container App Environment')
param envName string = 'clinical-trial-env909'

@description('The name of the Container App (Backend API)')
param backendAppName string = 'clinical-trial-api909'

@description('The name of the App Service Plan')
param aspName string = 'clinical-trial-ui-asp909'

@description('The name of the Frontend App Service Web App')
param frontendAppName string = 'clinical-trial-ui909'

// --- Variables for the Backend App Settings ---
param openai_endpoint string
param docintel_endpoint string

@secure()
param openai_api_key string

@secure()
param docintel_api_key string

param storage_account_name string

@secure()
param storage_access_key string

@secure()
param storage_connection_string string

param azure_client_id string = ''
param azure_tenant_id string = ''

@secure()
param azure_client_secret string = ''

param identityId string = ''
param identityClientId string = ''

// ==========================================
// 1. NEW BACKEND: AZURE CONTAINER APPS
// ==========================================

// 1a. Container Registry (Admin Enabled)
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// 1b. Log Analytics Workspace (Required for ACA)
resource law 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: lawName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
  }
}

// 1c. Container App Environment (The Cluster)
resource env 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: !empty(acaEnvSubnetId) ? {
      infrastructureSubnetId: acaEnvSubnetId
      internal: false
    } : null
  }
}

// 1d. The Container App (Backend API)
resource backend 'Microsoft.App/containerApps@2023-05-01' = {
  name: backendAppName
  location: location
  identity: !empty(identityId) ? {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  } : null
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'openai-api-key'
          value: openai_api_key
        }
        {
          name: 'docintel-api-key'
          value: docintel_api_key
        }
        {
          name: 'storage-access-key'
          value: storage_access_key
        }
        {
          name: 'storage-connection-string'
          value: storage_connection_string
        }
        {
          name: 'azure-client-secret'
          value: empty(azure_client_secret) ? 'placeholder' : azure_client_secret
        }
      ]
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.name
          passwordSecretRef: 'acr-password'
        }
      ]
      ingress: {
        external: true
        targetPort: 8000
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      scale: {
        minReplicas: 2
        maxReplicas: 10
        rules: [
          {
            name: 'http-concurrency-scaling'
            custom: {
              type: 'http'
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
      containers: [
        {
          name: 'api-worker'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          resources: {
            cpu: 1
            memory: '2.0Gi'
          }
          env: [
            {
              name: 'OPENAI_ENDPOINT'
              value: openai_endpoint
            }
            {
              name: 'OPENAI_API_KEY'
              secretRef: 'openai-api-key'
            }
            {
              name: 'OPENAI_API_VERSION'
              value: '2024-02-15-preview'
            }
            {
              name: 'DOCINTEL_ENDPOINT'
              value: docintel_endpoint
            }
            {
              name: 'DOCINTEL_API_KEY'
              secretRef: 'docintel-api-key'
            }
            {
              name: 'DOCINTEL_API_VERSION'
              value: '2023-10-01'
            }
            {
              name: 'STORAGE_ACCOUNT_NAME'
              value: storage_account_name
            }
            {
              name: 'STORAGE_ACCOUNT_KEY'
              secretRef: 'storage-access-key'
            }
            {
              name: 'STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'ENTRA_CLIENT_ID'
              value: azure_client_id
            }
            {
              name: 'ENTRA_TENANT_ID'
              value: azure_tenant_id
            }
            {
              name: 'ENTRA_CLIENT_SECRET'
              secretRef: 'azure-client-secret'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identityClientId
            }
          ]
        }
      ]
    }
  }
}

// ==========================================
// 2. FRONTEND APP SERVICE
// ==========================================

resource asp_frontend 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: aspName
  location: location
  sku: {
    name: 'B2'
  }
  kind: 'linux'
  properties: {
    reserved: true // Required for Linux OS
  }
}

resource frontend 'Microsoft.Web/sites@2022-09-01' = {
  name: frontendAppName
  location: location
  properties: {
    serverFarmId: asp_frontend.id
    virtualNetworkSubnetId: !empty(integrationSubnetId) ? integrationSubnetId : null
    publicNetworkAccess: !empty(deployerIp) ? 'Enabled' : publicNetworkAccess
    #disable-next-line BCP037
    scmPublicNetworkAccess: 'Enabled'
    siteConfig: {
      vnetRouteAllEnabled: true
      alwaysOn: true
      linuxFxVersion: 'NODE|20-lts'
      appCommandLine: 'pm2 serve /home/site/wwwroot --no-daemon --spa'
      ipSecurityRestrictions: !empty(deployerIp) ? [
        {
          ipAddress: '${deployerIp}/32'
          action: 'Allow'
          priority: 100
          name: 'AllowDeployer'
          description: 'Allow access from developer machine'
        }
      ] : []
      scmIpSecurityRestrictions: !empty(deployerIp) ? [
        {
          ipAddress: '${deployerIp}/32'
          action: 'Allow'
          priority: 100
          name: 'AllowDeployer'
          description: 'Allow deployment from developer machine'
        }
      ] : []
      scmIpSecurityRestrictionsUseMain: false
    }
  }
}

// --- Private Endpoint for Frontend App Service ---
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-04-01' = if (!empty(subnetId)) {
  name: 'frontend-private-endpoint'
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'frontend-link-connection'
        properties: {
          privateLinkServiceId: frontend.id
          groupIds: [
            'sites'
          ]
        }
      }
    ]
  }
}

// --- Private DNS Zone Group for Frontend App Service ---
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-04-01' = if (!empty(subnetId) && !empty(dnsZoneId)) {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'frontend-dns-config'
        properties: {
          privateDnsZoneId: dnsZoneId
        }
      }
    ]
  }
}

// --- Outputs: Required by the Bash Script ---
output backend_hostname string = backend.properties.configuration.ingress.fqdn
output storage_account_name string = storage_account_name
output frontend_hostname string = frontend.properties.defaultHostName
