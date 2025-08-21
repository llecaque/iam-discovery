# -*- coding: utf-8 -*-
"""
Une mini-application Flask pour servir le tableau de bord d'audit IAM en plusieurs pages distinctes.

Cette application a plusieurs fonctions :
1. Servir des pages HTML distinctes via des routes dédiées.
2. Fournir un point d'accès API '/api/data' pour charger dynamiquement toutes les données
   JSON nécessaires au tableau de bord.
"""
import os
import json
from flask import Flask, jsonify, render_template_string, abort

# Initialise l'application Flask
app = Flask(__name__)

# --- Modèles HTML ---

# Modèle de base partagé par toutes les pages
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP IAM Audit Dashboard</title>
    <script src="https://cdn.tailwindcss.com" referrerpolicy="strict-origin-when-cross-origin"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" referrerpolicy="strict-origin-when-cross-origin">
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .nav-active { border-color: #4f46e5; color: #4f46e5; background-color: #eef2ff; }
        .item-active { background-color: #c7d2fe; font-weight: 500; }
    </style>
</head>
<body class="bg-slate-50 text-slate-800">
    <div class="container mx-auto p-4 md:p-8">
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-slate-900">GCP IAM Audit Dashboard</h1>
            <p class="text-slate-500 mt-1">Interactively browse and filter your generated audit reports.</p>
        </header>

        <!-- Barre de Navigation -->
        <div class="mb-6 border-b border-slate-200">
            <nav class="flex -mb-px space-x-6">
                <a href="/" class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm {% if page == 'effective-access' %}nav-active{% else %}border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300{% endif %}">Effective Access</a>
                <a href="/users" class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm {% if page == 'by-user' %}nav-active{% else %}border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300{% endif %}">By User</a>
                <a href="/groups" class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm {% if page == 'by-group' %}nav-active{% else %}border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300{% endif %}">By Group</a>
                <a href="/user-details" class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm {% if page == 'user-details' %}nav-active{% else %}border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300{% endif %}">User Access Details</a>
                
                <!-- Menu déroulant pour les statistiques -->
                <div class="relative" x-data="{ open: false }" @mouseleave="open = false">
                    <button @mouseover="open = true" class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-1 {% if page.startswith('stats') %}nav-active{% else %}border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300{% endif %}">
                        <span>Statistics</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                    </button>
                    <div x-show="open" x-transition class="absolute z-10 mt-0 w-64 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
                        <div class="py-1">
                            <a href="/stats/users-per-role-project" class="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Users per Role/Project</a>
                            <a href="/stats/members-per-group" class="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Members per Group</a>
                            <a href="/stats/access-per-group" class="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Access Count per Group</a>
                            <a href="/stats/direct-access-count" class="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Direct Access per User</a>
                            <a href="/stats/groups-per-user" class="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Group Count per User</a>
                        </div>
                    </div>
                </div>
            </nav>
        </div>

        <!-- Contenu de la page -->
        <main>
            {{ content | safe }}
        </main>
    </div>

    <!-- Script JS -->
    <script>
        {{ script | safe }}
    </script>
</body>
</html>
"""

# --- Contenus des pages ---

EFFECTIVE_ACCESS_PAGE = """<div class="p-6 bg-white rounded-lg shadow-sm"><h2 class="text-xl font-semibold mb-4">Effective Access by Role & Project</h2><input type="text" id="filter-input" class="w-full p-2 border border-slate-300 rounded-md" placeholder="Filter by role, project, or user..."><div class="mt-4 overflow-x-auto"><table class="min-w-full divide-y divide-slate-200"><thead class="bg-slate-50"><tr><th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Role</th><th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Project</th><th class="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Users with Access</th></tr></thead><tbody id="data-table" class="bg-white divide-y divide-slate-200"></tbody></table></div></div>"""
USER_PAGE = """<div class="p-6 bg-white rounded-lg shadow-sm"><h2 class="text-xl font-semibold mb-4">Explore by User</h2><input type="text" id="user-filter" class="w-full p-2 border border-slate-300 rounded-md" placeholder="Filter users by email..."><div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4"><div id="user-list-container" class="md:col-span-1 max-h-96 overflow-y-auto border rounded-md p-2 bg-slate-50"></div><div id="user-details-container" class="md:col-span-2"><p class="text-slate-500 p-4 text-center">Select a user from the list to see their details.</p></div></div></div>"""
GROUP_PAGE = """<div class="p-6 bg-white rounded-lg shadow-sm"><h2 class="text-xl font-semibold mb-4">Explore by Group</h2><input type="text" id="group-filter" class="w-full p-2 border border-slate-300 rounded-md" placeholder="Filter groups by email..."><div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4"><div id="group-list-container" class="md:col-span-1 max-h-96 overflow-y-auto border rounded-md p-2 bg-slate-50"></div><div id="group-details-container" class="md:col-span-2"><p class="text-slate-500 p-4 text-center">Select a group from the list to see its details.</p></div></div></div>"""
USER_DETAILS_PAGE = """<div class="p-6 bg-white rounded-lg shadow-sm"><h2 class="text-xl font-semibold mb-4">Explore by User (Effective Access Details)</h2><input type="text" id="user-filter" class="w-full p-2 border border-slate-300 rounded-md" placeholder="Filter users by email..."><div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4"><div id="user-list-container" class="md:col-span-1 max-h-96 overflow-y-auto border rounded-md p-2 bg-slate-50"></div><div id="user-details-container" class="md:col-span-2"><p class="text-slate-500 p-4 text-center">Select a user from the list to see their detailed effective access.</p></div></div></div>"""
STATS_PAGE_TEMPLATE = """<div class="p-6 bg-white rounded-lg shadow-sm"><div id="stats-container"></div></div>"""

# --- Scripts JavaScript ---

JS_BASE = """
let allData = {};
async function initialize() {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) throw new Error('Network response was not ok.');
        allData = await response.json();
        if (typeof pageSpecificInitialize === 'function') {
            pageSpecificInitialize();
        }
    } catch (error) {
        console.error('Failed to load data:', error);
        alert("Error loading data from the API. Make sure the 'json' directory and its files exist, and the Flask app is running correctly.");
    }
}
document.addEventListener('DOMContentLoaded', initialize);
"""

JS_EFFECTIVE_ACCESS = JS_BASE + """
function pageSpecificInitialize() {
    renderEffectiveAccess(allData.effective);
    document.getElementById('filter-input').addEventListener('input', (e) => {
        renderEffectiveAccess(allData.effective, e.target.value);
    });
}
function renderEffectiveAccess(data, filter = '') {
    const tableBody = document.getElementById('data-table');
    let html = '';
    const lowerFilter = filter.toLowerCase();
    Object.entries(data).forEach(([key, users]) => {
        const [role, project] = key.split('@');
        const userList = users.join(', ');
        if (role.toLowerCase().includes(lowerFilter) || project.toLowerCase().includes(lowerFilter) || userList.toLowerCase().includes(lowerFilter)) {
            html += `<tr><td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">${role}</td><td class="px-6 py-4 whitespace-nowrap text-sm text-slate-500">${project}</td><td class="px-6 py-4 text-sm text-slate-500">${userList}</td></tr>`;
        }
    });
    tableBody.innerHTML = html || '<tr><td colspan="3" class="text-center py-4">No results found.</td></tr>';
}
"""

JS_USER_PAGE = JS_BASE + """
function pageSpecificInitialize() {
    const userFilterInput = document.getElementById('user-filter');
    const allUsers = Object.keys(allData.membership).sort();
    renderUserList(allUsers);
    userFilterInput.addEventListener('input', () => {
        const filter = userFilterInput.value.toLowerCase();
        const filteredUsers = allUsers.filter(user => user.toLowerCase().includes(filter));
        renderUserList(filteredUsers);
    });
    document.getElementById('user-list-container').addEventListener('click', (e) => {
        const targetButton = e.target.closest('button.user-item');
        if (targetButton) {
            const userEmail = targetButton.dataset.user;
            renderUserDetails(userEmail);
            document.querySelectorAll('.user-item').forEach(item => item.classList.remove('item-active'));
            targetButton.classList.add('item-active');
        }
    });
}
function renderUserList(users) {
    const userListContainer = document.getElementById('user-list-container');
    userListContainer.innerHTML = users.length ? users.map(user => `<button data-user="${user}" class="user-item block w-full text-left p-2 text-sm rounded-md hover:bg-indigo-100">${user}</button>`).join('') : '<p class="p-2 text-sm text-slate-500">No users found.</p>';
}
function renderUserDetails(user) {
    const container = document.getElementById('user-details-container');
    let directHtml = '<li>No direct access found.</li>';
    if (allData.direct[user] && allData.direct[user].length > 0) {
        directHtml = allData.direct[user].map(p => `<li><span class="font-semibold">${p.role}</span> on <span class="text-indigo-600">${p.project}</span></li>`).join('');
    }
    let groupsHtml = '<li>Not a member of any groups.</li>';
    if (allData.membership[user] && allData.membership[user].length > 0) {
        groupsHtml = allData.membership[user].map(g => `<li>${g}</li>`).join('');
    }
    container.innerHTML = `<div class="p-4 border rounded-lg bg-white"><h3 class="text-lg font-semibold text-slate-900">${user}</h3><div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6"><div><h4 class="font-medium text-slate-700">Direct Access</h4><ul class="mt-2 list-disc list-inside text-sm text-slate-600 space-y-1">${directHtml}</ul></div><div><h4 class="font-medium text-slate-700">Group Memberships</h4><ul class="mt-2 list-disc list-inside text-sm text-slate-600 space-y-1">${groupsHtml}</ul></div></div></div>`;
}
"""

JS_GROUP_PAGE = JS_BASE + """
function pageSpecificInitialize() {
    const groupFilterInput = document.getElementById('group-filter');
    const allGroups = Object.keys(allData.groupAccess).sort();
    renderGroupList(allGroups);
    groupFilterInput.addEventListener('input', () => {
        const filter = groupFilterInput.value.toLowerCase();
        const filteredGroups = allGroups.filter(group => group.toLowerCase().includes(filter));
        renderGroupList(filteredGroups);
    });
    document.getElementById('group-list-container').addEventListener('click', (e) => {
        const targetButton = e.target.closest('button.group-item');
        if (targetButton) {
            const groupEmail = targetButton.dataset.group;
            renderGroupDetails(groupEmail);
            document.querySelectorAll('.group-item').forEach(item => item.classList.remove('item-active'));
            targetButton.classList.add('item-active');
        }
    });
}
function renderGroupList(groups) {
    const groupListContainer = document.getElementById('group-list-container');
    groupListContainer.innerHTML = groups.length ? groups.map(group => `<button data-group="${group}" class="group-item block w-full text-left p-2 text-sm rounded-md hover:bg-indigo-100">${group}</button>`).join('') : '<p class="p-2 text-sm text-slate-500">No groups found.</p>';
}
function renderGroupDetails(group) {
    const container = document.getElementById('group-details-container');
    const { groupAccess, membership } = allData;
    const membersByGroup = {};
    Object.entries(membership).forEach(([user, groups]) => {
        groups.forEach(g => {
            if (!membersByGroup[g]) membersByGroup[g] = [];
            membersByGroup[g].push(user);
        });
    });
    let accessHtml = '<li>No GCP access found.</li>';
    if (groupAccess[group] && groupAccess[group].length > 0) {
        accessHtml = groupAccess[group].map(p => `<li><span class="font-semibold">${p.role}</span> on <span class="text-indigo-600">${p.project}</span></li>`).join('');
    }
    let membersHtml = '<li>No members found.</li>';
    if (membersByGroup[group] && membersByGroup[group].length > 0) {
        membersHtml = membersByGroup[group].map(m => `<li>${m}</li>`).join('');
    }
    container.innerHTML = `<div class="p-4 border rounded-lg bg-white"><h3 class="text-lg font-semibold text-slate-900">${group}</h3><div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6"><div><h4 class="font-medium text-slate-700">GCP Access</h4><ul class="mt-2 list-disc list-inside text-sm text-slate-600 space-y-1">${accessHtml}</ul></div><div><h4 class="font-medium text-slate-700">Members</h4><ul class="mt-2 list-disc list-inside text-sm text-slate-600 space-y-1">${membersHtml}</ul></div></div></div>`;
}
"""

JS_USER_DETAILS_PAGE = JS_BASE + """
function pageSpecificInitialize() {
    const userFilterInput = document.getElementById('user-filter');
    const allUsers = Object.keys(allData.userDetails).sort();
    renderUserList(allUsers);
    userFilterInput.addEventListener('input', () => {
        const filter = userFilterInput.value.toLowerCase();
        const filteredUsers = allUsers.filter(user => user.toLowerCase().includes(filter));
        renderUserList(filteredUsers);
    });
    document.getElementById('user-list-container').addEventListener('click', (e) => {
        const targetButton = e.target.closest('button.user-item');
        if (targetButton) {
            const userEmail = targetButton.dataset.user;
            renderUserDetails(userEmail);
            document.querySelectorAll('.user-item').forEach(item => item.classList.remove('item-active'));
            targetButton.classList.add('item-active');
        }
    });
}
function renderUserList(users) {
    const userListContainer = document.getElementById('user-list-container');
    userListContainer.innerHTML = users.length ? users.map(user => `<button data-user="${user}" class="user-item block w-full text-left p-2 text-sm rounded-md hover:bg-indigo-100">${user}</button>`).join('') : '<p class="p-2 text-sm text-slate-500">No users found.</p>';
}
function renderUserDetails(user) {
    const container = document.getElementById('user-details-container');
    let detailsHtml = '<li>No effective access details found.</li>';
    if (allData.userDetails[user] && allData.userDetails[user].length > 0) {
        detailsHtml = allData.userDetails[user].map(p => `<li><span class="font-semibold">${p.role}</span> on <span class="text-indigo-600">${p.project}</span> (Source: ${p.source})</li>`).join('');
    }
    container.innerHTML = `<div class="p-4 border rounded-lg bg-white"><h3 class="text-lg font-semibold text-slate-900">${user}</h3><div><h4 class="font-medium text-slate-700 mt-4">Effective Permissions</h4><ul class="mt-2 list-disc list-inside text-sm text-slate-600 space-y-1">${detailsHtml}</ul></div></div>`;
}
"""

JS_STATS_PAGE = JS_BASE + """
function pageSpecificInitialize() {
    const createListHtml = (title, dataObject) => {
        if (!dataObject) return `<h3 class="text-xl font-semibold mb-4">${title}</h3><p class="text-sm text-slate-500">Data not available.</p>`;
        let itemsHtml = Object.entries(dataObject)
            .map(([key, value]) => `<li class="flex justify-between items-center py-2 border-b"><span>${key}</span> <span class="font-semibold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">${value}</span></li>`)
            .join('');
        return `<h2 class="text-xl font-semibold mb-4">${title}</h2><ul class="space-y-2 text-sm">${itemsHtml}</ul>`;
    };
    const container = document.getElementById('stats-container');
    const path = window.location.pathname;
    if (path.includes('users-per-role-project')) {
        container.innerHTML = createListHtml('User Count per (Role@Project)', allData.summary.users_per_role_project_count);
    } else if (path.includes('members-per-group')) {
        container.innerHTML = createListHtml('Member Count per Group', allData.summary.members_per_group);
    } else if (path.includes('access-per-group')) {
        container.innerHTML = createListHtml('Access Count per Group', allData.summary.access_count_per_group);
    } else if (path.includes('direct-access-count')) {
        container.innerHTML = createListHtml('Direct Access Count per User', allData.summary.direct_access_count_by_user);
    } else if (path.includes('groups-per-user')) {
        container.innerHTML = createListHtml('Group Count per User', allData.summary.groups_per_user);
    }
}
"""

# --- Routes Flask ---

@app.route('/')
def effective_access_view():
    return render_template_string(BASE_TEMPLATE, page='effective-access', content=EFFECTIVE_ACCESS_PAGE, script=JS_EFFECTIVE_ACCESS)

@app.route('/users')
def by_user_view():
    return render_template_string(BASE_TEMPLATE, page='by-user', content=USER_PAGE, script=JS_USER_PAGE)

@app.route('/groups')
def by_group_view():
    return render_template_string(BASE_TEMPLATE, page='by-group', content=GROUP_PAGE, script=JS_GROUP_PAGE)

@app.route('/user-details')
def user_details_view():
    return render_template_string(BASE_TEMPLATE, page='user-details', content=USER_DETAILS_PAGE, script=JS_USER_DETAILS_PAGE)

@app.route('/stats/<stat_name>')
def summary_view(stat_name):
    valid_stats = ['users-per-role-project', 'members-per-group', 'access-per-group', 'direct-access-count', 'groups-per-user']
    if stat_name not in valid_stats:
        abort(404)
    return render_template_string(BASE_TEMPLATE, page='stats', content=STATS_PAGE_TEMPLATE, script=JS_STATS_PAGE)

@app.route('/api/data')
def get_all_data():
    """Charge et retourne toutes les données JSON nécessaires au tableau de bord."""
    json_files = {
        'effective': 'effective_access_by_role_project.json',
        'direct': 'user_direct_access.json',
        'membership': 'user_group_membership.json',
        'groupAccess': 'group_access_summary.json',
        'summary': 'numerical_summary.json',
        'userDetails': 'user_effective_access_details.json' # Nouveau
    }
    all_json_data = {}
    for key, filename in json_files.items():
        filepath = os.path.join('json', filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_json_data[key] = json.load(f)
        except FileNotFoundError:
            abort(404, description=f"Fichier de données manquant : {filename}")
        except json.JSONDecodeError:
            abort(500, description=f"Erreur de format dans le fichier : {filename}")
    return jsonify(all_json_data)

if __name__ == '__main__':
    print("Lancement du serveur Flask...")
    print("Ouvrez votre navigateur et allez sur http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
