async function pageSpecificInitialize(statKey, title) {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) throw new Error('Network response was not ok.');
        const allData = await response.json();
        renderSummary(statKey, title, allData.summary);
    } catch (error) {
        console.error('Failed to load data:', error);
    }
}

function renderSummary(statKey, title, data) {
    const createListHtml = (title, dataObject) => {
        if (!dataObject) return `<h2 class="text-xl font-semibold mb-4">${title}</h2><p class="text-sm text-slate-500">Data not available.</p>`;
        let itemsHtml = Object.entries(dataObject)
            .map(([key, value]) => `<li class="flex justify-between items-center py-2 border-b"><span>${key}</span> <span class="font-semibold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">${value}</span></li>`)
            .join('');
        return `<h2 class="text-xl font-semibold mb-4">${title}</h2><ul class="space-y-2 text-sm">${itemsHtml}</ul>`;
    };

    const container = document.getElementById('stats-container');
    let dataKey;
    switch(statKey) {
        case 'users-per-role-project': dataKey = 'users_per_role_project_count'; break;
        case 'members-per-group': dataKey = 'members_per_group'; break;
        case 'access-per-group': dataKey = 'access_count_per_group'; break;
        case 'direct-access-count': dataKey = 'direct_access_count_by_user'; break;
        case 'groups-per-user': dataKey = 'groups_per_user'; break;
    }

    if (dataKey && data[dataKey]) {
        container.innerHTML = createListHtml(title, data[dataKey]);
    } else {
        container.innerHTML = `<h2 class="text-xl font-semibold mb-4">${title}</h2><p class="text-sm text-slate-500">Data not available for this statistic.</p>`
    }
}