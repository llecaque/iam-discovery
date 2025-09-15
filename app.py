# -*- coding: utf-8 -*-
"""
A Flask application to serve the GCP IAM audit dashboard.

This version is refactored to run as a stateless service (e.g., on Cloud Run).
It reads its data from a Google Cloud Storage (GCS) bucket instead of the
local filesystem. The bucket name must be provided via the GCS_BUCKET_NAME
environment variable.
"""
import os
import json
from flask import Flask, jsonify, render_template, abort
from google.cloud import storage
from google.api_core.exceptions import NotFound

# ==============================================================================
# 1. INITIALISATION & CONFIGURATION
# ==============================================================================
app = Flask(__name__)

# --- GCS Configuration ---
# Initialize the GCS client. It will automatically use the runtime
# service account's credentials when deployed on GCP.
try:
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    storage_client = storage.Client() if GCS_BUCKET_NAME else None
except Exception as e:
    # This might fail in a local environment without gcloud setup,
    # but is essential for cloud deployment.
    print(f"Warning: Could not initialize GCS client. App will not work without it. Error: {e}")
    storage_client = None
    GCS_BUCKET_NAME = None


# ==============================================================================
# 2. FLASK ROUTES
# Each function corresponds to a page of the application.
# ==============================================================================

@app.route('/')
def effective_access_view():
    return render_template('effective_access.html', page='effective-access')

@app.route('/users')
def by_user_view():
    return render_template('by_user.html', page='by-user')

@app.route('/groups')
def by_group_view():
    return render_template('by_group.html', page='by-group')

@app.route('/user-details')
def user_details_view():
    return render_template('user_details.html', page='user-details')

@app.route('/stats/<stat_name>')
def summary_view(stat_name):
    valid_stats = [
        'users-per-role-project', 'members-per-group', 'access-per-group',
        'direct-access-count', 'groups-per-user'
    ]
    if stat_name not in valid_stats:
        abort(404)

    titles = {
        'users-per-role-project': 'User Count per (Role@Project)',
        'members-per-group': 'Member Count per Group',
        'access-per-group': 'Access Count per Group',
        'direct-access-count': 'Direct Access Count per User',
        'groups-per-user': 'Group Count per User'
    }

    return render_template('stats.html', page='stats', stat_key=stat_name, title=titles[stat_name])


@app.route('/api/data')
def get_all_data():
    """
    [MODIFIED] Loads all necessary JSON data from the GCS bucket and
    returns it as a single API response.
    """
    if not GCS_BUCKET_NAME or not storage_client:
        abort(500, description="FATAL: GCS_BUCKET_NAME environment variable is not set or client failed to initialize.")

    json_files = {
        'effective': 'effective_access_by_role_project.json',
        'direct': 'user_direct_access.json',
        'membership': 'user_group_membership.json',
        'groupAccess': 'group_access_summary.json',
        'summary': 'numerical_summary.json',
        'userDetails': 'user_effective_access_details.json'
    }
    all_json_data = {}

    try:
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
    except Exception as e:
        abort(500, description=f"Could not connect to GCS bucket '{GCS_BUCKET_NAME}'. Error: {e}")

    for key, filename in json_files.items():
        try:
            blob = bucket.blob(filename)
            data_string = blob.download_as_string()
            all_json_data[key] = json.loads(data_string)
        except NotFound:
            abort(404, description=f"Data file '{filename}' not found in GCS bucket '{GCS_BUCKET_NAME}'.")
        except json.JSONDecodeError:
            abort(500, description=f"Format error in data file: {filename}")
        except Exception as e:
            abort(500, description=f"An unexpected error occurred while reading '{filename}': {e}")

    return jsonify(all_json_data)

# ==============================================================================
# 3. APPLICATION ENTRY POINT
# ==============================================================================
if __name__ == '__main__':
    # Determine the port - use PORT from environment for Cloud Run, or 8080 for local
    PORT = int(os.environ.get("PORT", 8080))
    print("Starting Flask server for IAM Dashboard...")
    print(f"Navigate to https://127.0.0.1:{PORT} in your browser.")
    # Use ssl_context='adhoc' to enable a self-signed HTTPS certificate for local development
    app.run(host='0.0.0.0', port=PORT, debug=True, ssl_context='adhoc')

