@description('Location for the OpenAI resource.')
param location string = resourceGroup().location

@description('Optional: Subnet ID for the Private Endpoint')
param subnetId string = ''

@description('Optional: Private DNS Zone ID for OpenAI')
param dnsZoneId string = ''

@description('Public network access status for the OpenAI resource')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Disabled'

@description('The name of the OpenAI resource.')
param openaiName string = 'clinicaltrialopenai909'

@description('Optional: The principal ID of the Managed Identity to assign roles to.')
param principalId string = ''

/*
========================================
Azure OpenAI Account
========================================
*/
resource openai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openaiName
  location: location
  kind: 'OpenAI'

  sku: {
    name: 'S0'
  }

  tags: {
    costcenter: '500'
    workload: 'sandbox'
  }

  properties: {
    customSubDomainName: toLower(openaiName)
    publicNetworkAccess: publicNetworkAccess
  }
}

/*
========================================
Deployment Delay (1 Minute)
========================================
*/
resource delayScript 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'openai-deployment-delay'
  location: location
  kind: 'AzurePowerShell'
  dependsOn: [
    openai
  ]
  properties: {
    azPowerShellVersion: '12.0'
    scriptContent: 'Start-Sleep -Seconds 60'
    timeout: 'PT5M'
    cleanupPreference: 'OnSuccess'
    retentionInterval: 'P1D'
  }
}

/*
========================================
GPT-4o Deployment
========================================
*/
resource gpt4o 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openai
  name: 'gpt4o'

  #disable-next-line no-unnecessary-dependson
  dependsOn: [
    delayScript
  ]

  sku: {
    name: 'GlobalStandard'
    capacity: 1
  }

  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

/*
========================================
GPT-4o Mini Deployment
========================================
*/
resource gpt4oMini 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openai
  name: 'gpt4o-mini'

  dependsOn: [
    gpt4o
  ]

  sku: {
    name: 'GlobalStandard'
    capacity: 1
  }

  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
  }
}

/*
========================================
Private Endpoint (Optional)
========================================
*/
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-04-01' = if (!empty(subnetId)) {
  name: 'openai-private-endpoint'
  location: location

  properties: {
    subnet: {
      id: subnetId
    }

    privateLinkServiceConnections: [
      {
        name: 'openai-link-connection'
        properties: {
          privateLinkServiceId: openai.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

/*
========================================
Private DNS Zone Group (Optional)
========================================
*/
resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-04-01' = if (!empty(subnetId) && !empty(dnsZoneId)) {
  parent: privateEndpoint
  name: 'default'

  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'openai-dns-config'

        properties: {
          privateDnsZoneId: dnsZoneId
        }
      }
    ]
  }
}

/*
========================================
Role Assignment for Managed Identity
========================================
*/
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(openai.id, principalId, 'Cognitive Services OpenAI User')
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4fbc-af51-cd5413fcf214')
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

/*
========================================
Outputs
=======================================
*/
output openai_endpoint string = openai.properties.endpoint

#disable-next-line outputs-should-not-contain-secrets
output openai_api_key string = openai.listKeys().key1

output openai_api_version string = '2024-02-15-preview'