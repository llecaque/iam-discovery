# -*- coding: utf-8 -*-
"""
Summarizes individual audit reports into multiple, dimension-specific files.

This script reads all '.txt' files from a specified audit directory, parses them,
and aggregates the data to create five distinct reports, all saved in a 'json' folder:
1.  user_direct_access.json: A map of each user to their direct project roles.
2.  user_group_membership.json: A JSON mapping users to their group memberships.
3.  group_access_summary.json: A map of each group to its project roles.
4.  numerical_summary.json: A summary of various counts.
5.  user_effective_access_details.json: A detailed breakdown of every permission
    for each user, showing the source (direct or a specific group).

How to Run:
1. Ensure you have an 'audit' directory populated with .txt report files.
2. Run this script from your terminal:
   python this_script_name.py --audit-dir ./audit
"""
import os
import json
import argparse
import re
from collections import defaultdict

# --- CONFIGURATION ---

# The names of the output report files.
USER_ACCESS_FILENAME = 'user_direct_access.json'
USER_GROUPS_FILENAME = 'user_group_membership.json'
GROUP_ACCESS_FILENAME = 'group_access_summary.json'
NUMERICAL_SUMMARY_FILENAME = 'numerical_summary.json'
EFFECTIVE_ACCESS_FILENAME = 'effective_access_by_role_project.json'
USER_EFFECTIVE_ACCESS_FILENAME = 'user_effective_access_details.json' # Nouveau fichier
JSON_OUTPUT_DIR = 'json'

# --- SCRIPT LOGIC ---

def parse_audit_reports(audit_dir):
    """
    Parses all .txt audit reports and aggregates data into three structures.

    Args:
        audit_dir (str): The path to the directory containing the .txt files.

    Returns:
        tuple: Contains three dictionaries for user access, group membership,
               and group access.
    """
    if not os.path.isdir(audit_dir):
        print(f"ERROR: Directory not found at '{audit_dir}'")
        return None, None, None

    # Initialize data structures
    direct_access_by_user = defaultdict(list)
    group_membership_by_user = defaultdict(set)
    access_by_group = defaultdict(list)

    print(f"Scanning directory '{audit_dir}' for audit reports...")

    for filename in os.listdir(audit_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(audit_dir, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.readlines()

            # State variables for parsing
            current_user_email = None
            current_group_email = None
            parsing_direct_access = False
            parsing_group_access = False

            # Find the user for this report
            match = re.search(r"Access Report for: .* \((.*)\)|Access Report for: (.*)", content[0])
            if match:
                current_user_email = match.group(1) or match.group(2)
            
            if not current_user_email:
                print(f"  - WARNING: Could not identify user in '{filename}'. Skipping.")
                continue
                
            print(f"  - Processing report for: {current_user_email}")

            for line in content:
                line = line.strip()

                # State changes
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

                # Data extraction
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
    """Main function to orchestrate the summary creation."""
    parser = argparse.ArgumentParser(description='Summarize GCP IAM audit reports into multiple files.')
    parser.add_argument(
        "--audit-dir",
        required=True,
        help="Path to the directory containing the individual .txt audit reports."
    )
    args = parser.parse_args()

    # Create output directory for JSON files
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

    user_access, user_groups, group_access = parse_audit_reports(args.audit_dir)

    if user_access is not None:
        print("\n--- Generating Reports ---")
        
        # --- Calculate Effective & Numerical Data ---
        
        effective_users_per_role_project = defaultdict(set)
        user_effective_access_details = defaultdict(list)

        # Process direct access
        for user, permissions in user_access.items():
            for perm in permissions:
                key = f"{perm['role']}@{perm['project']}"
                effective_users_per_role_project[key].add(user)
                user_effective_access_details[user].append({
                    "project": perm['project'],
                    "role": perm['role'],
                    "source": "direct"
                })
        
        # Process inherited access
        for user, groups in user_groups.items():
            for group_email in groups:
                group_permissions = group_access.get(group_email, [])
                for perm in group_permissions:
                    key = f"{perm['role']}@{perm['project']}"
                    effective_users_per_role_project[key].add(user)
                    user_effective_access_details[user].append({
                        "project": perm['project'],
                        "role": perm['role'],
                        "source": f"group: {group_email}"
                    })
        
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
            "groups_per_user": dict(sorted(groups_per_user.items()))
        }

        # --- Save Reports ---
        user_access_path = os.path.join(JSON_OUTPUT_DIR, USER_ACCESS_FILENAME)
        group_access_path = os.path.join(JSON_OUTPUT_DIR, GROUP_ACCESS_FILENAME)
        user_groups_path = os.path.join(JSON_OUTPUT_DIR, USER_GROUPS_FILENAME)
        numerical_summary_path = os.path.join(JSON_OUTPUT_DIR, NUMERICAL_SUMMARY_FILENAME)
        effective_access_path = os.path.join(JSON_OUTPUT_DIR, EFFECTIVE_ACCESS_FILENAME)
        user_effective_access_path = os.path.join(JSON_OUTPUT_DIR, USER_EFFECTIVE_ACCESS_FILENAME)
        
        user_groups_serializable = {user: sorted(list(groups)) for user, groups in user_groups.items()}
        effective_access_serializable = {key: sorted(list(users)) for key, users in effective_users_per_role_project.items()}

        save_json_report(user_access_path, user_access, "user direct access")
        save_json_report(user_groups_path, user_groups_serializable, "user group membership")
        save_json_report(group_access_path, group_access, "group access summary")
        save_json_report(numerical_summary_path, numerical_summary, "numerical summary")
        save_json_report(effective_access_path, effective_access_serializable, "effective access by role/project")
        save_json_report(user_effective_access_path, dict(user_effective_access_details), "user effective access details") # Nouveau rapport
    else:
        print("\nReport generation failed due to errors.")

if __name__ == '__main__':
    main()
