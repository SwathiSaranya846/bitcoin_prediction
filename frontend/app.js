/* frontend/app.js */

// ==================== CONFIG ====================
const API_URL = 'http://localhost:5000';

// ==================== STATE ====================
let priceChart = null;

// ==================== DOM ELEMENTS ====================
const predictionForm = () => document.getElementById('predictionForm');
const predictBtn = () => document.getElementById('predictBtn');
const predictionResult = () => document.getElementById('predictionResult');
const loading = () => document.getElementById('loading');
const toast = () => document.getElementById('toast');

// ==================== INITIALIZE ====================
document.addEventListener('DOMContentLoaded', () => {
    attachHandlers();
    loadStats();
    loadHistory();
    setCurrentMonth();
});

// Also attach immediately in case the script runs after DOMContentLoaded
try { attachHandlers(); } catch (e) { /* ignore */ }

// ==================== HELPERS ====================
function attachHandlers() {
    const form = predictionForm();
    if (form) {
        form.addEventListener('submit', handlePredict);
    }
}

function setCurrentMonth() {
    const monthSelect = document.getElementById('month');
    if (!monthSelect) return;
    const currentMonth = new Date().getMonth() + 1;
    monthSelect.value = currentMonth;
}

function showLoading() {
    const l = loading(); if (l) l.classList.remove('hidden');
    const btn = predictBtn(); if (btn) btn.disabled = true;
}

function hideLoading() {
    const l = loading(); if (l) l.classList.add('hidden');
    const btn = predictBtn(); if (btn) btn.disabled = false;
}

function showToast(message, type = 'success') {
    const t = toast(); if (!t) return;
    t.textContent = message;
    t.className = `toast ${type}`;
    setTimeout(() => t.classList.add('hidden'), 3000);
}

function formatCurrency(value) {
    return '$' + Number(value).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function displayPrediction(result) {
    const container = predictionResult();
    if (!container || !result) return;
    container.classList.remove('hidden');
    container.classList.toggle('up', result.prediction?.direction === 'UP');
    container.classList.toggle('down', result.prediction?.direction === 'DOWN');

    const predictionText = document.getElementById('predictionText');
    const confidenceText = document.getElementById('confidenceText');
    const upProb = document.getElementById('upProb');
    const downProb = document.getElementById('downProb');

    if (predictionText) predictionText.textContent = result.prediction?.direction || '--';
    if (confidenceText) confidenceText.textContent = result.prediction ? `${(result.prediction.confidence*100).toFixed(1)}%` : '--';
    if (upProb) upProb.textContent = result.prediction ? `${(result.prediction.up_prob*100).toFixed(1)}%` : '--';
    if (downProb) downProb.textContent = result.prediction ? `${(result.prediction.down_prob*100).toFixed(1)}%` : '--';
}

// ==================== API CALLS ====================
async function loadStats() {
    try {
        const res = await fetch(`${API_URL}/api/stats`);
        const json = await res.json();
        if (json.success) {
            const stats = json.data || {};
            document.getElementById('totalRecords').textContent = stats.total_records || '--';
            document.getElementById('maxPrice').textContent = formatCurrency(stats.max_price || 0);
            document.getElementById('minPrice').textContent = formatCurrency(stats.min_price || 0);
            document.getElementById('avgPrice').textContent = formatCurrency(stats.avg_price || 0);
        }
    } catch (e) {
        console.error('loadStats error', e);
    }
}

async function loadHistory() {
    try {
        const res = await fetch(`${API_URL}/api/history?limit=60`);
        const json = await res.json();
        if (!json.success) return;
        const rows = json.data || [];
        // build arrays for chart
        const labels = rows.map(r => r.date).reverse();
        const prices = rows.map(r => Number(r.close_price || r.close || 0)).reverse();
        renderChart(labels, prices);
    } catch (e) {
        console.error('loadHistory error', e);
    }
}

function renderChart(labels, data) {
    const ctx = document.getElementById('priceChart');
    if (!ctx) return;
    if (priceChart) priceChart.destroy();
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Close Price',
                data,
                borderColor: '#F7931A',
                backgroundColor: 'rgba(247,147,26,0.1)',
                fill: true,
            }]
        },
        options: {maintainAspectRatio: false}
    });
}

// ==================== PREDICT HANDLER ====================
async function handlePredict(e) {
    e.preventDefault();
    console.log('[UI] handlePredict called');
    const open = Number(document.getElementById('open').value || 0);
    const high = Number(document.getElementById('high').value || 0);
    const low = Number(document.getElementById('low').value || 0);
    const close = Number(document.getElementById('close').value || 0);
    const month = Number(document.getElementById('month').value || (new Date().getMonth()+1));

    showLoading();
    try {
        console.log('[UI] sending payload', {open, high, low, close, month});
        const res = await fetch(`${API_URL}/api/predict`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({open, high, low, close, month})
        });

        const json = await res.json();
        console.log('[UI] prediction response', json);
        if (!json.success) {
            showToast('Prediction failed: ' + (json.error || 'unknown'), 'error');
            console.error('Predict error', json);
            hideLoading();
            return;
        }

        displayPrediction(json);
        showToast('Prediction complete');
    } catch (err) {
        console.error('Prediction request failed', err);
        showToast('Prediction request failed', 'error');
    } finally {
        hideLoading();
    }
}
