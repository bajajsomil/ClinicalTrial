# Novartis Clinical Trial App - One-Click Deployment

This repository contains the Terraform infrastructure configurations and bash scripts to perform a **one-click deployment** for both the backend (Python/FastAPI) and frontend (React/Node) applications into Azure.

## Required Folder Structure

For the deployment script to work correctly, your files **must** be arranged in the exact folder structure shown below. 

> **CRITICAL**: The folder containing this deployment script MUST be named `terraform`, otherwise the script will fail.

```text
project-root/          <-- Your overarching main directory
│
├── frontend/          <-- EXACT FOLDER NAME: Your Frontend code
│   ├── package.json   (Must contain the standard npm "build" script)
│   ├── src/           (React/Vite source files)
│   └── ...
│
├── backend/           <-- EXACT FOLDER NAME: Your Backend code
│   ├── requirements.txt
│   ├── app.py         (Assuming FastAPI/Uvicorn entry point)
│   └── ...
│
└── terraform/         <-- EXACT FOLDER NAME
    ├── deploy.sh
    ├── main.tf
    ├── modules/
    └── ...
```

---

## How to Deploy (One-Click)

Once your folder structure perfectly matches the above, open your terminal (bash), navigate to this `terraform` directory, and run the following commands:

1. **Make the deployment script executable:**
   ```bash
   chmod +x deploy.sh
   ```

2. **Execute the one-click deployment script:**
   ```bash
   ./deploy.sh
   ```
   
**What the script does automatically:**
- Initializes and applies Azure Infrastructure via Terraform.
- Computes dependencies and compresses your `backend` folder, safely skipping virtual environments/cache files.
- Triggers a background deployment of the backend.
- Dynamically fetches output values (URLs, storage components) from Terraform.
- Injects a formatted `.env` natively into the `frontend` directory.
- Runs `npm install` and `npm run build` on your local frontend codebase.
- Zips the required static assets and deploys the newly built frontend.

---

## ⚙️ Configuration & Customization 

If you want to change **Resource Names**, **Locations**, or other Azure properties, you must be careful to update specific configurations in both the Terraform files **AND** the deployment bash script.

### 1. Changing Resource Group & Location
If you modify your Resource Group name (currently configured as `clinical-trial11`) or Location (currently `East US 2`), you must change it in two places:

* **File: `main.tf`**
  ```hcl
  resource "azurerm_resource_group" "rg" {
    name     = "clinical-trial11"   # Change here
    location = "East US 2"          # Change here
  }
  ```
* **File: `deploy.sh`**
  Update the `--resource-group` flags explicitly on **Lines 20, 23, and 54** to match your new Resource Group name.

### 2. Changing App Service Names (Frontend / Backend API)
Currently, your app services are named `clinical-trial-api11` and `clinical-trial-ui11`.

* **File: `modules/app_service/main.tf`**
  ```hcl
  # Backend app service name (Line 44)
  name = "clinical-trial-api11"

  # Frontend app service name (Line 83)
  name = "clinical-trial-ui11"
  ```
* **File: `deploy.sh`**
  Update the `--name` arguments directly pointing to the web app naming within the bash statements on **Lines 20, 23, and 54** so Azure CLI knows which deployments to aim for.

### 3. Other Core Components
If you'd like to adjust naming for additional backend services, look for naming allocations in their respective sub-directories:
- **Storage**: `modules/storage/main.tf`
- **OpenAI**: `modules/openai/main.tf`
- **Doc Intelligence**: `modules/doc_intelligence/main.tf`

> **Note:** For any internal IP/hostname routing changes resulting from Terraform, `deploy.sh` will seamlessly collect Terraform's stdout to update the matching variables and dynamically populate your frontend framework context. Keep the outputs block in `main.tf` cleanly mapped!
