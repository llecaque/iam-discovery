let allData = {};

async function initialize() {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) throw new Error('Network response was not ok.');
        allData = await response.json();
        
        // Déclenche l'initialisation spécifique à la page si elle existe
        const page = document.body.dataset.page;
        if (page === 'effective-access') setupEffectiveAccess();
        if (page === 'by-user') setupUserView();
        if (page === 'by-group') setupGroupView();
        if (page === 'user-details') setupUserDetailsView();

    } catch (error) {
        console.error('Failed to load data:', error);
        alert("Error loading data from the API. Make sure the 'json' directory and its files exist, and the Flask app is running correctly.");
    }
}

function setupEffectiveAccess() {
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

function setupUserView() {
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

function setupGroupView() {
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

function setupUserDetailsView() {
    const userFilterInput = document.getElementById('user-filter');
    const allUsers = Object.keys(allData.userDetails).sort();
    renderUserListForDetails(allUsers);
    userFilterInput.addEventListener('input', () => {
        const filter = userFilterInput.value.toLowerCase();
        const filteredUsers = allUsers.filter(user => user.toLowerCase().includes(filter));
        renderUserListForDetails(filteredUsers);
    });
    document.getElementById('user-list-container').addEventListener('click', (e) => {
        const targetButton = e.target.closest('button.user-item');
        if (targetButton) {
            const userEmail = targetButton.dataset.user;
            renderEffectiveUserDetails(userEmail);
            document.querySelectorAll('.user-item').forEach(item => item.classList.remove('item-active'));
            targetButton.classList.add('item-active');
        }
    });
}

function renderUserListForDetails(users) {
    const userListContainer = document.getElementById('user-list-container');
    userListContainer.innerHTML = users.length ? users.map(user => `<button data-user="${user}" class="user-item block w-full text-left p-2 text-sm rounded-md hover:bg-indigo-100">${user}</button>`).join('') : '<p class="p-2 text-sm text-slate-500">No users found.</p>';
}

function renderEffectiveUserDetails(user) {
    const container = document.getElementById('user-details-container');
    let detailsHtml = '<li class="text-slate-500">No effective access details found.</li>';
    let logLinksHtml = '<li class="text-slate-500">No projects with access found.</li>';

    if (allData.userDetails[user] && allData.userDetails[user].length > 0) {
        const userPermissions = allData.userDetails[user];
        const cursorTimestamp = new Date().toISOString();
        
        detailsHtml = userPermissions.map(p => {
            return `<li class="py-2 border-b border-slate-100">
                        <span class="font-semibold">${p.role}</span> on 
                        <span class="text-indigo-600">${p.project}</span> 
                        <br>
                        <span class="text-xs text-slate-500">(Source: ${p.source})</span>
                    </li>`;
        }).join('');

        const uniqueProjects = [...new Set(userPermissions.map(p => p.project))];

        if (uniqueProjects.length > 0) {
            logLinksHtml = uniqueProjects.sort().map(project => {
                const logQuery = `protoPayload.authenticationInfo.principalEmail="${user}"`;
                const encodedQuery = encodeURIComponent(logQuery);
                const logUrl = `https://console.cloud.google.com/logs/query;query=${encodedQuery};cursorTimestamp=${cursorTimestamp};duration=P30D?project=${project}`;
                
                // Récupère le nombre de logs depuis les nouvelles données
                const logCounts = allData.summary.log_counts_by_user || {};
                const userLogData = logCounts[user] || {};
                const count = userLogData[project];
                let countText = '(N/A requests)';
                if (typeof count === 'number' && count >= 0) {
                    countText = `(${count} requests)`;
                } else if (count === -1) {
                    countText = `(Permission Denied)`;
                }

                return `<li class="flex items-center justify-between py-2">
                            <div>
                                <span class="text-indigo-600">${project}</span>
                                <span class="text-xs text-slate-500 ml-2">${countText}</span>
                            </div>
                            <a href="${logUrl}" target="_blank" title="View user activity logs for this project" class="text-xs text-indigo-600 hover:text-indigo-800 font-medium bg-indigo-50 hover:bg-indigo-100 px-2 py-1 rounded-full">
                                View Logs
                            </a>
                        </li>`;
            }).join('');
        }
    }

    container.innerHTML = `<div class="p-4 border rounded-lg bg-white">
                               <h3 class="text-lg font-semibold text-slate-900">${user}</h3>
                               <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                                   <div>
                                       <h4 class="font-medium text-slate-700">Effective Permissions</h4>
                                       <ul class="mt-2 text-sm text-slate-600">${detailsHtml}</ul>
                                   </div>
                                   <div>
                                       <h4 class="font-medium text-slate-700">Project Log Links</h4>
                                       <ul class="mt-2 text-sm text-slate-600">${logLinksHtml}</ul>
                                   </div>
                               </div>
                           </div>`;
}

document.addEventListener('DOMContentLoaded', initialize);
