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
    let detailsHtml = '<li>No effective access details found.</li>';
    if (allData.userDetails[user] && allData.userDetails[user].length > 0) {
        detailsHtml = allData.userDetails[user].map(p => `<li><span class="font-semibold">${p.role}</span> on <span class="text-indigo-600">${p.project}</span> (Source: ${p.source})</li>`).join('');
    }
    container.innerHTML = `<div class="p-4 border rounded-lg bg-white"><h3 class="text-lg font-semibold text-slate-900">${user}</h3><div><h4 class="font-medium text-slate-700 mt-4">Effective Permissions</h4><ul class="mt-2 list-disc list-inside text-sm text-slate-600 space-y-1">${detailsHtml}</ul></div></div>`;
}

// Ajoute un attribut de données au body pour identifier la page actuelle
const path = window.location.pathname;
if (path === '/') document.body.dataset.page = 'effective-access';
else if (path === '/users') document.body.dataset.page = 'by-user';
else if (path === '/groups') document.body.dataset.page = 'by-group';
else if (path === '/user-details') document.body.dataset.page = 'user-details';

document.addEventListener('DOMContentLoaded', initialize);