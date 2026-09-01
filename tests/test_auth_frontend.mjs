import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';


const calls = [];
const response = (body) => ({
    ok: true,
    status: 200,
    json: async () => body,
});
const apiContext = {
    console,
    URLSearchParams,
    state: { token: null },
    localStorage: { setItem: () => {} },
    logout: async () => {},
    utils: { showAlert: () => {} },
    fetch: async (url, options = {}) => {
        calls.push({ url, options });
        if (url.endsWith('/login')) return response({ access_token: 'access-token' });
        if (url.includes('/users?')) return response({ total: 1, items: [] });
        return response({ access_token: 'refreshed-token' });
    },
};

vm.createContext(apiContext);
vm.runInContext(
    `${fs.readFileSync('static/apis.js', 'utf8')}\nthis.__apis = apis;`,
    apiContext,
);

await apiContext.__apis.login('frontend@example.com', '2468');
assert.equal(calls[0].url, '/api/v1/users/login');
assert.equal(calls[0].options.headers['Content-Type'], 'application/json');
assert.deepEqual(
    JSON.parse(calls[0].options.body),
    { email: 'frontend@example.com', password: '2468' },
);

await apiContext.__apis.refresh();
assert.equal(calls[1].url, '/api/v1/users/token/refresh');

await apiContext.__apis.adminGetUsers({ search: 'frontend', department: 'MEDICAL' });
assert.equal(
    calls[2].url,
    '/api/v1/users?search=frontend&department=MEDICAL',
);

await apiContext.__apis.adminUpdateUserRole(7, 'STAFF');
assert.equal(calls[3].url, '/api/v1/users/7/role');
assert.equal(calls[3].options.method, 'PATCH');
assert.deepEqual(JSON.parse(calls[3].options.body), { role: 'STAFF' });


const elements = {};
const getElement = (id) => {
    if (!elements[id]) {
        elements[id] = {
            innerHTML: '',
            innerText: '',
            value: '',
            style: {},
        };
    }
    return elements[id];
};
const pageContext = {
    console,
    state: {
        currentPage: '/admin/users',
        user: { id: 1, role: 'ADMIN' },
    },
    document: { getElementById: getElement },
    utils: {
        loadTemplate: async () => '<table><tbody id="admin-users-list"></tbody></table>',
        formatPhoneNumber: (value) => value,
        showAlert: () => {},
    },
    apis: {
        adminGetUsers: async () => ({
            total: 1,
            items: [{
                id: 7,
                name: '테스트 사용자',
                email: 'frontend@example.com',
                department: 'MEDICAL',
                phone_number: '01000000000',
                role: 'STAFF',
                is_active: true,
            }],
        }),
    },
    navigate: () => {},
    confirm: () => false,
    logout: () => {},
    checkAuth: async () => {},
    FileReader: class {},
};

vm.createContext(pageContext);
vm.runInContext(
    `${fs.readFileSync('static/pages.js', 'utf8')}\nthis.__pages = pages;`,
    pageContext,
);

await pageContext.__pages.renderAdminUsers();
assert.match(elements['admin-users-list'].innerHTML, /frontend@example\.com/);
assert.match(elements['admin-users-list'].innerHTML, /value="STAFF" selected/);
