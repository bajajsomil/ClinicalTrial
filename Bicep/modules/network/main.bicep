@description('Location for all network resources.')
param location string = resourceGroup().location

@description('Name of the Virtual Network')
param vnetName string = 'clinical-trial-vnet'

@description('Optional: The IP address of the deployer to allow for deployment and access')
param deployerIp string = ''

@description('Optional: Additional user allowed IP address or CIDR to whitelist')
param userAllowedIp string = ''

@description('Optional: Log Analytics Workspace ID for diagnostic settings.')
param logAnalyticsWorkspaceId string = ''

/*
========================================
Network Security Groups (NSGs)
========================================
*/

resource applicationNsg 'Microsoft.Network/networkSecurityGroups@2023-04-01' = {
  name: '${vnetName}-app-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-HTTPS-Inbound'
        properties: {
          description: 'Allow all incoming HTTPS traffic on port 443'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
    ]
  }
}

// Dynamic rule generation for web subnet NSG to safely handle optional IPs
var defaultWebRules = [
  {
    name: 'Allow-AppSubnet-Inbound'
    properties: {
      description: 'Allow inbound from application subnet'
      protocol: 'Tcp'
      sourcePortRange: '*'
      destinationPortRange: '443'
      sourceAddressPrefix: '10.0.1.0/24'
      destinationAddressPrefix: '10.0.2.0/24'
      access: 'Allow'
      priority: 100
      direction: 'Inbound'
    }
  }
  {
    name: 'Allow-DbSubnet-Inbound'
    properties: {
      description: 'Allow inbound from db subnet'
      protocol: 'Tcp'
      sourcePortRange: '*'
      destinationPortRange: '443'
      sourceAddressPrefix: '10.0.3.0/24'
      destinationAddressPrefix: '10.0.2.0/24'
      access: 'Allow'
      priority: 110
      direction: 'Inbound'
    }
  }
  {
    name: 'Allow-AcaEnvSubnet-Inbound'
    properties: {
      description: 'Allow inbound from Container App Environment subnet (required for backend to access OpenAI)'
      protocol: 'Tcp'
      sourcePortRange: '*'
      destinationPortRange: '443'
      sourceAddressPrefix: '10.0.0.0/24'
      destinationAddressPrefix: '10.0.2.0/24'
      access: 'Allow'
      priority: 115
      direction: 'Inbound'
    }
  }
]

var deployerRule = !empty(deployerIp) ? [
  {
    name: 'Allow-DeployerIp-Inbound'
    properties: {
      description: 'Allow inbound from deployer public IP'
      protocol: 'Tcp'
      sourcePortRange: '*'
      destinationPortRange: '443'
      sourceAddressPrefix: contains(deployerIp, '/') ? deployerIp : '${deployerIp}/32'
      destinationAddressPrefix: '10.0.2.0/24'
      access: 'Allow'
      priority: 120
      direction: 'Inbound'
    }
  }
] : []

var userAllowedRule = !empty(userAllowedIp) ? [
  {
    name: 'Allow-UserAllowedIp-Inbound'
    properties: {
      description: 'Allow inbound from user allowed IP'
      protocol: 'Tcp'
      sourcePortRange: '*'
      destinationPortRange: '443'
      sourceAddressPrefix: contains(userAllowedIp, '/') ? userAllowedIp : '${userAllowedIp}/32'
      destinationAddressPrefix: '10.0.2.0/24'
      access: 'Allow'
      priority: 130
      direction: 'Inbound'
    }
  }
] : []

var denyAllWebRule = [
  {
    name: 'Deny-AllOther-Inbound'
    properties: {
      description: 'Deny all other inbound traffic to web subnet'
      protocol: '*'
      sourcePortRange: '*'
      destinationPortRange: '*'
      sourceAddressPrefix: '*'
      destinationAddressPrefix: '10.0.2.0/24'
      access: 'Deny'
      priority: 200
      direction: 'Inbound'
    }
  }
]

resource webNsg 'Microsoft.Network/networkSecurityGroups@2023-04-01' = {
  name: '${vnetName}-web-nsg'
  location: location
  properties: {
    securityRules: concat(defaultWebRules, deployerRule, userAllowedRule, denyAllWebRule)
  }
}

resource dbNsg 'Microsoft.Network/networkSecurityGroups@2023-04-01' = {
  name: '${vnetName}-db-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-WebSubnet-Inbound'
        properties: {
          description: 'Allow inbound from web subnet'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '10.0.2.0/24'
          destinationAddressPrefix: '10.0.3.0/24'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'Allow-AcaEnvSubnet-Inbound'
        properties: {
          description: 'Allow inbound from Container App Environment subnet (required for backend to access Storage)'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '10.0.0.0/24'
          destinationAddressPrefix: '10.0.3.0/24'
          access: 'Allow'
          priority: 110
          direction: 'Inbound'
        }
      }
      {
        name: 'Deny-AllOther-Inbound'
        properties: {
          description: 'Deny all other inbound traffic to db subnet'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '10.0.3.0/24'
          access: 'Deny'
          priority: 200
          direction: 'Inbound'
        }
      }
    ]
  }
}

// --- Diagnostic Settings for NSGs ---
resource applicationNsgDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${applicationNsg.name}-diagnostics'
  scope: applicationNsg
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'NetworkSecurityGroupEvent'
        enabled: true
      }
      {
        category: 'NetworkSecurityGroupRuleCounter'
        enabled: true
      }
    ]
  }
}

resource webNsgDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${webNsg.name}-diagnostics'
  scope: webNsg
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'NetworkSecurityGroupEvent'
        enabled: true
      }
      {
        category: 'NetworkSecurityGroupRuleCounter'
        enabled: true
      }
    ]
  }
}

resource dbNsgDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(logAnalyticsWorkspaceId)) {
  name: '${dbNsg.name}-diagnostics'
  scope: dbNsg
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'NetworkSecurityGroupEvent'
        enabled: true
      }
      {
        category: 'NetworkSecurityGroupRuleCounter'
        enabled: true
      }
    ]
  }
}

/*
========================================
Virtual Network
========================================
*/

resource vnet 'Microsoft.Network/virtualNetworks@2023-04-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/21'
      ]
    }
    subnets: [
      {
        name: 'aca-env-subnet'
        properties: {
          addressPrefix: '10.0.0.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          delegations: [
            {
              name: 'aca-delegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'application-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          networkSecurityGroup: {
            id: applicationNsg.id
          }
        }
      }
      {
        name: 'web-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          networkSecurityGroup: {
            id: webNsg.id
          }
        }
      }
      {
        name: 'db-subnet'
        properties: {
          addressPrefix: '10.0.3.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          networkSecurityGroup: {
            id: dbNsg.id
          }
        }
      }
      {
        name: 'integration-subnet'
        properties: {
          addressPrefix: '10.0.4.0/26'
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          delegations: [
            {
              name: 'appservice-delegation'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
    ]
  }
}

// Private DNS Zones
resource privateDnsZoneApp 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.azurewebsites.net'
  location: 'global'
}

resource privateDnsZoneOpenAI 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.openai.azure.com'
  location: 'global'
}

resource privateDnsZoneBlob 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  location: 'global'
}

resource privateDnsZoneCognitive 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.cognitiveservices.azure.com'
  location: 'global'
}

resource privateDnsZoneKeyVault 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
}

// VNet Links to Private DNS Zones
resource vnetLinkApp 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneApp
  name: '${vnetName}-link-app'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource vnetLinkOpenAI 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneOpenAI
  name: '${vnetName}-link-openai'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource vnetLinkBlob 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneBlob
  name: '${vnetName}-link-blob'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource vnetLinkCognitive 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneCognitive
  name: '${vnetName}-link-cognitive'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource vnetLinkKeyVault 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneKeyVault
  name: '${vnetName}-link-keyvault'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

output vnetId string = vnet.id
output appSubnetId string = '${vnet.id}/subnets/application-subnet'
output webSubnetId string = '${vnet.id}/subnets/web-subnet'
output dbSubnetId string = '${vnet.id}/subnets/db-subnet'
output acaEnvSubnetId string = '${vnet.id}/subnets/aca-env-subnet'
output integrationSubnetId string = '${vnet.id}/subnets/integration-subnet'

output dnsZoneIdApp string = privateDnsZoneApp.id
output dnsZoneIdOpenAI string = privateDnsZoneOpenAI.id
output dnsZoneIdBlob string = privateDnsZoneBlob.id
output dnsZoneIdCognitive string = privateDnsZoneCognitive.id
output dnsZoneIdKeyVault string = privateDnsZoneKeyVault.id
