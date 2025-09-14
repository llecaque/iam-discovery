# -*- coding: utf-8 -*-
"""
Summarizes individual audit reports into multiple, dimension-specific files.

This script reads all '.txt' files from a specified audit directory, parses them,
and aggregates the data to create multiple distinct reports.

It now also queries the Google Cloud Logging API to count user activity per project.
"""
import os
import json
import argparse
import re
import datetime
from collections import defaultdict
from google.cloud import logging
from google.api_core import exceptions as gcp_exceptions

# --- CONFIGURATION ---
JSON_OUTPUT_DIR = 'json'
# ... (noms de fichiers)

# --- NOUVELLE FONCTION POUR COMPTER LES LOGS ---
def count_user_logs_for_project(project_id: str, user_email: str, days: int = 30) -> int:
    """Counts log entries for a specific user in a given project."""
    try:
        client = logging.Client(project=project_id)
        start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        start_time_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        filter_str = (
            f'protoPayload.authenticationInfo.principalEmail="{user_email}" AND '
            f'timestamp >= "{start_time_str}"'
        )

        # Utilise un iterateur et compte les éléments pour être plus efficace
        entries_iterator = client.list_entries(filter_=filter_str, page_size=1000)
        entry_count = sum(1 for _ in entries_iterator)
        
        print(f"    - Found {entry_count} log entries for {user_email} in project {project_id}")
        return entry_count
    except gcp_exceptions.PermissionDenied:
        print(f"    - WARNING: Permission denied to read logs in project '{project_id}'. Skipping log count.")
        return -1 # Code pour indiquer une erreur de permission
    except Exception as e:
        print(f"    - WARNING: An error occurred fetching logs for {user_email} in {project_id}: {e}")
        return -1

# --- LOGIQUE PRINCIPALE (MISE À JOUR) ---
def parse_audit_reports(audit_dir):
    # ... (le reste de la fonction parse_audit_reports reste identique)
    if not os.path.isdir(audit_dir):
        print(f"ERROR: Directory not found at '{audit_dir}'")
        return None, None, None
    direct_access_by_user = defaultdict(list)
    group_membership_by_user = defaultdict(set)
    access_by_group = defaultdict(list)
    print(f"Scanning directory '{audit_dir}' for audit reports...")
    for filename in os.listdir(audit_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(audit_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
            current_user_email = None
            current_group_email = None
            parsing_direct_access = False
            parsing_group_access = False
            match = re.search(r"Access Report for: .* \((.*)\)|Access Report for: (.*)", content[0])
            if match:
                current_user_email = match.group(1) or match.group(2)
            if not current_user_email:
                print(f"  - WARNING: Could not identify user in '{filename}'. Skipping.")
                continue
            print(f"  - Processing report for: {current_user_email}")
            for line in content:
                line = line.strip()
                if "Direct GCP Access" in line:
                    parsing_direct_access = True
                    parsing_group_access = False
                    continue
                if "Inherited GCP Access" in line:
                    parsing_direct_access = False
                    parsing_group_access = True
                    continue
                if parsing_group_access and "Access for Group:" in line:
                    match = re.search(r"\((.*)\)", line)
                    if match:
                        current_group_email = match.group(1)
                        group_membership_by_user[current_user_email].add(current_group_email)
                if "Project:" in line:
                    project_id = line.split(":", 1)[1].strip()
                elif "Role:" in line:
                    role = line.split(":", 1)[1].strip()
                    if parsing_direct_access:
                        entry = {"project": project_id, "role": role}
                        if entry not in direct_access_by_user[current_user_email]:
                            direct_access_by_user[current_user_email].append(entry)
                    elif parsing_group_access and current_group_email:
                        entry = {"project": project_id, "role": role}
                        if entry not in access_by_group[current_group_email]:
                            access_by_group[current_group_email].append(entry)
    return dict(direct_access_by_user), dict(group_membership_by_user), dict(access_by_group)

def save_json_report(filename, data, description):
    """Saves a dictionary to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Successfully created {description} report at '{filename}'")
    except IOError as e:
        print(f"ERROR: Could not save report to '{filename}'. Details: {e}")

def main():
    parser = argparse.ArgumentParser(description='Summarize GCP IAM audit reports into multiple files.')
    parser.add_argument("--audit-dir", required=True, help="Path to the directory containing the individual .txt audit reports.")
    args = parser.parse_args()

    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    user_access, user_groups, group_access = parse_audit_reports(args.audit_dir)

    if user_access is not None:
        print("\n--- Generating Reports ---")
        
        # --- Calcul des données effectives et numériques ---
        effective_users_per_role_project = defaultdict(set)
        user_effective_access_details = defaultdict(list)
        all_user_project_pairs = defaultdict(set)

        for user, permissions in user_access.items():
            for perm in permissions:
                key = f"{perm['role']}@{perm['project']}"
                effective_users_per_role_project[key].add(user)
                user_effective_access_details[user].append({"project": perm['project'], "role": perm['role'], "source": "direct"})
                all_user_project_pairs[user].add(perm['project'])
        
        for user, groups in user_groups.items():
            for group_email in groups:
                group_permissions = group_access.get(group_email, [])
                for perm in group_permissions:
                    key = f"{perm['role']}@{perm['project']}"
                    effective_users_per_role_project[key].add(user)
                    user_effective_access_details[user].append({"project": perm['project'], "role": perm['role'], "source": f"group: {group_email}"})
                    all_user_project_pairs[user].add(perm['project'])

        # --- NOUVEAU : Récupération des décomptes de logs ---
        print("\n--- Fetching User Log Counts (this may take a while) ---")
        log_counts_by_user = defaultdict(dict)
        for user, projects in all_user_project_pairs.items():
            for project in projects:
                count = count_user_logs_for_project(project, user)
                log_counts_by_user[user][project] = count

        # --- Calcul des données numériques ---
        users_per_role_project_count = {key: len(users) for key, users in effective_users_per_role_project.items()}
        members_per_group = defaultdict(int)
        for groups in user_groups.values():
            for group in groups:
                members_per_group[group] += 1
        direct_access_count_by_user = {user: len(perms) for user, perms in user_access.items()}
        access_count_per_group = {group: len(perms) for group, perms in group_access.items()}
        groups_per_user = {user: len(groups) for user, groups in user_groups.items()}

        numerical_summary = {
            "members_per_group": dict(sorted(members_per_group.items())),
            "users_per_role_project_count": dict(sorted(users_per_role_project_count.items())),
            "direct_access_count_by_user": dict(sorted(direct_access_count_by_user.items())),
            "access_count_per_group": dict(sorted(access_count_per_group.items())),
            "groups_per_user": dict(sorted(groups_per_user.items())),
            "log_counts_by_user": dict(log_counts_by_user) # Ajout des nouvelles données
        }

        # --- Sauvegarde des rapports ---
        # ... (le reste de la fonction main reste identique)
        user_access_path = os.path.join(JSON_OUTPUT_DIR, 'user_direct_access.json')
        group_access_path = os.path.join(JSON_OUTPUT_DIR, 'group_access_summary.json')
        user_groups_path = os.path.join(JSON_OUTPUT_DIR, 'user_group_membership.json')
        numerical_summary_path = os.path.join(JSON_OUTPUT_DIR, 'numerical_summary.json')
        effective_access_path = os.path.join(JSON_OUTPUT_DIR, 'effective_access_by_role_project.json')
        user_effective_access_path = os.path.join(JSON_OUTPUT_DIR, 'user_effective_access_details.json')
        
        user_groups_serializable = {user: sorted(list(groups)) for user, groups in user_groups.items()}
        effective_access_serializable = {key: sorted(list(users)) for key, users in effective_users_per_role_project.items()}

        save_json_report(user_access_path, user_access, "user direct access")
        save_json_report(user_groups_path, user_groups_serializable, "user group membership")
        save_json_report(group_access_path, group_access, "group access summary")
        save_json_report(numerical_summary_path, numerical_summary, "numerical summary")
        save_json_report(effective_access_path, effective_access_serializable, "effective access by role/project")
        save_json_report(user_effective_access_path, dict(user_effective_access_details), "user effective access details")
    else:
        print("\nReport generation failed due to errors.")

if __name__ == '__main__':
    main()
