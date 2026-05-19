targetScope = 'subscription'

extension 'br:mcr.microsoft.com/bicep/extensions/microsoftgraph/v1.0:0.1.9-preview'

@description('The Object ID of the user or Service Principal running the deployment')
#disable-next-line no-unused-params
param currentUserId string

@description('The Object ID of the Microsoft Graph Service Principal in your tenant')
#disable-next-line no-unused-params
param msgraphSpObjectId string

@description('The hostname of the backend App Service')
param backend_hostname string

@description('The base name of the deployment')
param baseName string

// --- Constants ---
var appName = 'ClinicalApp-${baseName}'
var msgraphAppId = '00000003-0000-0000-c000-000000000000'

// Fixed: Added the missing '3' at the end of the GUID
var userReadScopeId = 'e1fe6dd8-ba39-40d6-baa8-502871459f93'
var userReadAllRoleId = 'df021288-bdef-4463-88db-98f22de89214'

// =========================
// App Registration
// =========================
resource app 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: appName
  displayName: appName
  
  // Note: 'owners' removed as the new extension handles this dynamically
  
  web: {
    redirectUris: [
      'http://localhost:8000/callback'
      'https://${backend_hostname}/callback'
    ]
    implicitGrantSettings: {
      enableAccessTokenIssuance: false
      enableIdTokenIssuance: true
    }
  }

  requiredResourceAccess: [
    {
      resourceAppId: msgraphAppId
      resourceAccess: [
        {
          id: userReadScopeId
          type: 'Scope'
        }
        {
          id: userReadAllRoleId
          type: 'Role'
        }
      ]
    }
  ]
}

// =========================
// Service Principal
// =========================
resource sp 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: app.appId
}

// =========================
// Outputs
// =========================
output client_id string = app.appId
output tenant_id string = tenant().tenantId
output client_secret string = 'placeholder'
