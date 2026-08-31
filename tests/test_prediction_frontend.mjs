import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';


const elements = {};
const getElement = (id) => {
    if (!elements[id]) {
        elements[id] = {
            innerHTML: '',
            innerText: '',
            src: '',
            style: {},
            onclick: null,
        };
    }
    return elements[id];
};

let navigatedPath = null;
const context = {
    console,
    state: { currentPage: '/patients/7/medical-records/10' },
    document: { getElementById: getElement },
    utils: {
        loadTemplate: async () => '<div>record detail</div>',
        showAlert: () => {},
    },
    apis: {
        getMedicalRecord: async () => ({
            id: 10,
            patient_id: 7,
            chart_number: 'CH-10',
            symptoms: '기침',
            created_at: '2026-08-31T10:00:00Z',
            xray_image_url: '/media/xrays/xray.png',
        }),
        getMedicalRecordAnalyses: async () => ([{
            id: 3,
            record_id: 10,
            is_pneumonia: true,
            confidence: 91.25,
            heatmap_url: null,
            created_at: '2026-08-31T10:01:00Z',
            ai_model: 'simple-cnn-v1',
        }]),
        predictPneumonia: async (recordId) => {
            assert.equal(recordId, 10);
        },
    },
    navigate: async (path) => {
        navigatedPath = path;
    },
};

vm.createContext(context);
const source = fs.readFileSync('static/pages.js', 'utf8');
vm.runInContext(`${source}\nthis.__pages = pages;`, context);

await context.__pages.renderRecordDetail(7, 10);

assert.match(elements['analysis-list'].innerHTML, /<th>ID<\/th>/);
assert.match(elements['analysis-list'].innerHTML, /Heatmap URL/);
assert.match(elements['analysis-list'].innerHTML, /<td>3<\/td>/);
assert.match(elements['analysis-list'].innerHTML, /<td>-<\/td>/);

await elements['predict-btn'].onclick();

assert.equal(navigatedPath, '/patients/7/medical-records/10');
