# IAM Discovery & Audit Toolchain

This project provides a suite of Python and shell scripts to audit and visualize user and group permissions in Google Cloud Platform (GCP) and Google Workspace.

The workflow is designed to first export all relevant IAM data, process it into a local cache, generate detailed reports, and finally, present the findings in an interactive web dashboard.

---

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Python 3.7+** and `pip`.
2.  **Google Cloud SDK (`gcloud` CLI):** Authenticated with an administrator account.
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```
3.  **Required Python Libraries:**
    ```bash
    pip install Flask google-api-python-client google-auth-httplib2
    ```
4.  **Enabled APIs:** Ensure the **Admin SDK API** is enabled in your GCP project.
    ```bash
    gcloud services enable admin.googleapis.com
    ```

---

## Workflow & Instructions

The process is divided into four main steps. Please execute them in order.

### Step 1: Export Project IAM Policies

This step uses a shell script to fetch the IAM policies for a predefined list of GCP projects and saves them as individual JSON files in a dated directory.

```bash
bash gcp-iam-export.sh
```

# IAM Discovery & Audit Toolchain

This project provides a suite of Python and shell scripts to audit and visualize user and group permissions in Google Cloud Platform (GCP) and Google Workspace.

The workflow is designed to first export all relevant IAM data, process it into a local cache, generate detailed reports, and finally, present the findings in an interactive web dashboard.

---

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Python 3.7+** and `pip`.
2.  **Google Cloud SDK (`gcloud` CLI):** Authenticated with an administrator account.
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```
3.  **Required Python Libraries:**
    ```bash
    pip install Flask google-api-python-client google-auth-httplib2
    ```
4.  **Enabled APIs:** Ensure the **Admin SDK API** is enabled in your GCP project.
    ```bash
    gcloud services enable admin.googleapis.com
    ```

---

## Workflow & Instructions

The process is divided into four main steps. Please execute them in order.

### Step 1: Export Project IAM Policies

This step uses a shell script to fetch the IAM policies for a predefined list of GCP projects and saves them as individual JSON files in a dated directory.

    ```bash
    bash gcp-iam-export.sh
    ```

This will create a new directory (e.g., 2025-08-21) containing the policy files.

### Step 2: Create the Local IAM Cache

This script processes the raw JSON policy files from the previous step and compiles them into a single, optimized iam_cache.json file. This cache is essential for the subsequent steps.

    ```bash
    python create_iam_cache.py --policy-dir <date_directory>
    ```


### Step 3: Generate Individual Audit Reports

This script uses the iam_cache.json to generate detailed .txt reports for each user. It can be run in two modes:

### A) Audit members of a specific Google Group:

    ```bash
    python gdpr-access-audit-local-json.py --group-email <group_email>
    ```

### B) Audit users from a CSV file:

The CSV must contain FirstName and LastName columns.

    ```bash
    python gdpr-access-audit-local-json.py --users-csv <path_to_csv>
    ```

This will create an audit directory filled with individual user reports.

### Step 4: Summarize Audit Data

This script parses all the .txt files in the audit/ directory and generates several summary JSON files in a json/ directory. These files are the data source for the web dashboard.

    ```bash
    python summary.py --audit-dir audit
    ```

### Step 5: Launch the Interactive Dashboard

Finally, run the Flask web application to visualize all the generated reports in your browser.

    ```bash
    python app.py
    ```

Once the server is running, open your web browser and navigate to:
http://127.0.0.1:5000