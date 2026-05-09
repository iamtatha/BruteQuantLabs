/**
 * BruteQuantLabs Dashboard Logic
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Relative paths from BruteQuantLabs/webpages/
    const TICKER_LIST_URL = '../../database/static_data/nifty_50.csv';
    const FUNDAMENTALS_DIR = '../../database/fundamentals_data/';
    const PRICES_DIR = '../../database/historical_data_yf/';

    let tickers = [];
    let currentSymbol = 'TCS';
    let chart = null;
    let lineSeries = null;
    let lastPrices = null;
    let lastInfo = null;

    // --- UI Elements ---
    const searchInput = document.getElementById('search-input');
    const searchDropdown = document.getElementById('search-dropdown');
    const stockNameEl = document.getElementById('stock-name');
    const symbolBadgeEl = document.getElementById('symbol-badge');
    const industryEl = document.getElementById('industry-label');
    const priceNowEl = document.getElementById('price-now');
    const priceDeltaEl = document.getElementById('price-delta');
    const metricsGridEl = document.getElementById('metrics-grid');
    const prosListEl = document.getElementById('pros-list');
    const consListEl = document.getElementById('cons-list');
    const peersTableBody = document.querySelector('#peers-table tbody');
    const peersTableHead = document.querySelector('#peers-table thead tr');
    const quarterlyTableBody = document.querySelector('#quarterly-table tbody');
    const quarterlyTableHead = document.querySelector('#quarterly-table thead tr');
    const annualTableBody = document.querySelector('#annual-table tbody');
    const annualTableHead = document.querySelector('#annual-table thead tr');
    const balanceSheetTableBody = document.querySelector('#balance-sheet-table tbody');
    const balanceSheetTableHead = document.querySelector('#balance-sheet-table thead tr');
    const cashFlowTableBody = document.querySelector('#cash-flow-table tbody');
    const cashFlowTableHead = document.querySelector('#cash-flow-table thead tr');
    const shareholdingQuarterlyTableBody = document.querySelector('#shareholding-quarterly-table tbody');
    const shareholdingQuarterlyTableHead = document.querySelector('#shareholding-quarterly-table thead tr');
    const shareholdingYearlyTableBody = document.querySelector('#shareholding-yearly-table tbody');
    const shareholdingYearlyTableHead = document.querySelector('#shareholding-yearly-table thead tr');


    async function init() {
        await loadTickers();
        setupSearch();
        await loadData(currentSymbol);
    }

    async function loadTickers() {
        try {
            const res = await fetch(TICKER_LIST_URL);
            const text = await res.text();
            tickers = text.split('\n').slice(1).map(line => {
                const parts = line.split(',');
                if (parts.length < 4) return null;
                return { symbol: parts[0], name: parts[1], industry: parts[2], yf: parts[3] };
            }).filter(t => t);
        } catch (e) {
            console.error("CSV Load Error", e);
            tickers = [{ symbol: 'RELIANCE', name: 'Reliance Industries Ltd.', industry: 'Energy', yf: 'RELIANCE.NS' }];
        }
    }

    function setupSearch() {
        searchInput.addEventListener('input', (e) => {
            const q = e.target.value.toUpperCase();
            if (!q) return searchDropdown.style.display = 'none';
            const matched = tickers.filter(t => t.symbol.includes(q) || t.name.toUpperCase().includes(q)).slice(0, 10);
            searchDropdown.innerHTML = matched.map(t => `
                <div class="search-item" data-sym="${t.symbol}">
                    <span class="sym">${t.symbol}</span>
                    <span class="nm">${t.name}</span>
                </div>
            `).join('');
            searchDropdown.style.display = matched.length ? 'block' : 'none';
        });

        searchDropdown.addEventListener('click', (e) => {
            const item = e.target.closest('.search-item');
            if (item) {
                searchInput.value = item.dataset.sym;
                searchDropdown.style.display = 'none';
                loadData(item.dataset.sym);
            }
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) searchDropdown.style.display = 'none';
        });
    }

    async function loadData(symbol) {
        currentSymbol = symbol;
        const info = tickers.find(t => t.symbol === symbol) || { symbol, yf: `${symbol}.NS`, name: symbol, industry: '' };

        try {
            const [fund, price] = await Promise.all([
                fetch(`${FUNDAMENTALS_DIR}${symbol}.json`).then(r => r.json()),
                fetch(`${PRICES_DIR}${info.yf}_yf.json`).then(r => r.json())
            ]);
            // console.log(fund, price);   
            render(fund, price, info);
        } catch (e) {
            console.error("Data Load Error", e);
            stockNameEl.textContent = "Data Not Found";
        }
    }

    function render(fund, prices, info) {
        lastPrices = prices;
        lastInfo = info;

        stockNameEl.textContent = info.name;
        symbolBadgeEl.textContent = info.symbol;
        industryEl.textContent = info.industry;

        const dates = Object.keys(prices).sort();
        const chartData = dates.map(d => ({ time: d, value: prices[d][`Close_${info.yf.trim()}`] }))
            .filter(d => d.value !== undefined && d.value !== null && !isNaN(d.value));

        if (chartData.length) {
            const latest = chartData[chartData.length - 1].value;
            const prev = chartData[chartData.length - 2]?.value || latest;
            const diff = latest - prev;
            const diffPct = prev !== 0 ? (diff / prev) * 100 : 0;



            priceNowEl.textContent = `₹${latest.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
            priceDeltaEl.textContent = `${diff >= 0 ? '▲' : '▼'} ${Math.abs(diff).toFixed(2)} (${diffPct.toFixed(2)}%)`;
            priceDeltaEl.className = `price-delta ${diff >= 0 ? 'up' : 'down'}`;

            updateChart(chartData);
        } else {
            priceNowEl.textContent = 'Data Not Available';
            priceDeltaEl.textContent = '';
        }

        metricsGridEl.innerHTML = Object.entries(fund.company_info).map(([k, v]) => `
            <div class="metric-card">
                <span class="m-label">${k}</span>
                <span class="m-value">${v}</span>
            </div>
        `).join('');

        renderHistoryTable();

        prosListEl.innerHTML = fund.analysis.PROS.map(p => `<li>${p}</li>`).join('');
        consListEl.innerHTML = fund.analysis.CONS.map(c => `<li>${c}</li>`).join('');

        if (fund.peers) {
            peersTableHead.innerHTML = fund.peers.headers.map(h => `<th>${h}</th>`).join('');
            const rowKeys = Object.keys(fund.peers).filter(k => k.endsWith('.'));
            peersTableBody.innerHTML = rowKeys.map(k => `
                <tr>${fund.peers[k].map((v, i) => `<td>${i === 0 ? `<b>${v}</b>` : v}</td>`).join('')}</tr>
            `).join('');
        }

        if (fund.quarterly) {
            // Add an empty header for row labels
            quarterlyTableHead.innerHTML =
                `<th>Metric</th>` +
                fund.quarterly.headers.map(h => `<th>${h}</th>`).join('');

            // Get all keys except headers
            const rowKeys = Object.keys(fund.quarterly).filter(k => k !== 'headers');

            quarterlyTableBody.innerHTML = rowKeys.map(key => {
                const values = fund.quarterly[key];

                return `
            <tr>
                <td><b>${key}</b></td>
                ${values.map(v => `<td>${v}</td>`).join('')}
            </tr>
        `;
            }).join('');
        }

        if (fund.annual) {
            // Add an empty header for row labels
            annualTableHead.innerHTML =
                `<th>Metric</th>` +
                fund.annual.headers.map(h => `<th>${h}</th>`).join('');

            // Get all keys except headers
            const rowKeys = Object.keys(fund.annual).filter(k => k !== 'headers');

            annualTableBody.innerHTML = rowKeys.map(key => {
                const values = fund.annual[key];

                return `
            <tr>
                <td><b>${key}</b></td>
                ${values.map(v => `<td>${v}</td>`).join('')}
            </tr>
        `;
            }).join('');
        }

        if (fund.balance_sheet) {
            // Add an empty header for row labels
            balanceSheetTableHead.innerHTML =
                `<th>Metric</th>` +
                fund.balance_sheet.headers.map(h => `<th>${h}</th>`).join('');

            // Get all keys except headers
            const rowKeys = Object.keys(fund.balance_sheet).filter(k => k !== 'headers');

            balanceSheetTableBody.innerHTML = rowKeys.map(key => {
                const values = fund.balance_sheet[key];

                return `
            <tr>
                <td><b>${key}</b></td>
                ${values.map(v => `<td>${v}</td>`).join('')}
            </tr>
        `;
            }).join('');
        }

        if (fund.cash_flow) {
            // Add an empty header for row labels
            cashFlowTableHead.innerHTML =
                `<th>Metric</th>` +
                fund.cash_flow.headers.map(h => `<th>${h}</th>`).join('');

            // Get all keys except headers
            const rowKeys = Object.keys(fund.cash_flow).filter(k => k !== 'headers');

            cashFlowTableBody.innerHTML = rowKeys.map(key => {
                const values = fund.cash_flow[key];

                return `
            <tr>
                <td><b>${key}</b></td>
                ${values.map(v => `<td>${v}</td>`).join('')}
            </tr>
        `;
            }).join('');
        }

        if (fund.shareholding_quarterly) {
            // Add an empty header for row labels
            shareholdingQuarterlyTableHead.innerHTML =
                `<th>Metric</th>` +
                fund.shareholding_quarterly.headers.map(h => `<th>${h}</th>`).join('');

            // Get all keys except headers
            const rowKeys = Object.keys(fund.shareholding_quarterly).filter(k => k !== 'headers');

            shareholdingQuarterlyTableBody.innerHTML = rowKeys.map(key => {
                const values = fund.shareholding_quarterly[key];

                return `
            <tr>
                <td><b>${key}</b></td>
                ${values.map(v => `<td>${v}</td>`).join('')}
            </tr>
        `;
            }).join('');
        }

        if (fund.shareholding_yearly) {
            // Add an empty header for row labels
            shareholdingYearlyTableHead.innerHTML =
                `<th>Metric</th>` +
                fund.shareholding_yearly.headers.map(h => `<th>${h}</th>`).join('');

            // Get all keys except headers
            const rowKeys = Object.keys(fund.shareholding_yearly).filter(k => k !== 'headers');

            shareholdingYearlyTableBody.innerHTML = rowKeys.map(key => {
                const values = fund.shareholding_yearly[key];

                return `
            <tr>
                <td><b>${key}</b></td>
                ${values.map(v => `<td>${v}</td>`).join('')}
            </tr>
        `;
            }).join('');
        }

        if (window.lucide) window.lucide.createIcons();
    }



    function updateChart(data) {
        const container = document.getElementById('chart-container');
        if (!chart) {
            chart = LightweightCharts.createChart(container, {
                layout: { textColor: '#9FB3C8', background: { type: 'solid', color: 'transparent' } },
                grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(150,150,150,0.1)' } },
                rightPriceScale: { borderVisible: false },
                timeScale: { borderVisible: false },
                crosshair: { mode: 0 }
            });
            lineSeries = chart.addSeries(LightweightCharts.LineSeries, {
                color: '#2563EB',
                lineWidth: 2,
                crosshairMarkerVisible: true
            });
            new ResizeObserver(() => chart.applyOptions({ width: container.clientWidth, height: container.clientHeight })).observe(container);
        }
        lineSeries.setData(data);
        chart.timeScale().fitContent();
    }

    function renderHistoryTable() {
        const tbody = document.querySelector('#history-table tbody');
        if (!lastPrices || !lastInfo) return;

        const timeframe = document.getElementById('timeframe-select').value;
        const allDates = Object.keys(lastPrices).sort().reverse();

        const now = new Date(allDates[0]);
        let cutoffDate = new Date(0); // ALL
        if (timeframe === '1W') cutoffDate = new Date(now.setDate(now.getDate() - 7));
        else if (timeframe === '1M') cutoffDate = new Date(now.setMonth(now.getMonth() - 1));
        else if (timeframe === '3M') cutoffDate = new Date(now.setMonth(now.getMonth() - 3));
        else if (timeframe === '6M') cutoffDate = new Date(now.setMonth(now.getMonth() - 6));
        else if (timeframe === '1Y') cutoffDate = new Date(now.setFullYear(now.getFullYear() - 1));

        const cutoffStr = cutoffDate.toISOString().split('T')[0];

        const filteredDates = timeframe === 'ALL' ? allDates : allDates.filter(d => d >= cutoffStr);


        tbody.innerHTML = filteredDates.map(d => {
            const data = lastPrices[d];
            const close = data[`Close_${lastInfo.yf.trim()}`];
            const high = data[`High_${lastInfo.yf.trim()}`];
            const low = data[`Low_${lastInfo.yf.trim()}`];
            const vol = data[`Volume_${lastInfo.yf.trim()}`];

            if (close === undefined) return '';

            return `<tr>
                <td>${d}</td>
                <td>₹${close.toFixed(2)}</td>
                <td>₹${high?.toFixed(2) || '-'}</td>
                <td>₹${low?.toFixed(2) || '-'}</td>
                <td>${vol ? vol.toLocaleString('en-IN') : '-'}</td>
            </tr>`;
        }).join('');
    }

    document.getElementById('timeframe-select').addEventListener('change', renderHistoryTable);

    document.getElementById('theme-toggle').addEventListener('click', () => {
        const isLight = document.body.getAttribute('data-theme') === 'light';
        document.body.setAttribute('data-theme', isLight ? 'dark' : 'light');
        const icon = document.getElementById('theme-icon');
        icon.setAttribute('data-lucide', isLight ? 'sun' : 'moon');
        if (window.lucide) window.lucide.createIcons();
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-box')) {
            document.getElementById('search-dropdown').style.display = 'none';
        }
    });

    // Collapsible sections
    document.querySelectorAll('.collapsible-header').forEach(header => {
        header.addEventListener('click', () => {
            const content = header.parentElement.querySelector('.collapsed-content');
            const icon = header.querySelector('.collapse-icon');
            if (content.style.display === 'none') {
                content.style.display = 'block';
                if (icon) icon.style.transform = 'rotate(0deg)';
            } else {
                content.style.display = 'none';
                if (icon) icon.style.transform = 'rotate(-90deg)';
            }
        });
    });

    // Smooth scrolling for nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetSec = document.getElementById(targetId);
            if (targetSec) {
                targetSec.scrollIntoView({ behavior: 'smooth' });
                // Optionally expand the section if it is collapsed
                const content = targetSec.querySelector('.collapsed-content');
                const icon = targetSec.querySelector('.collapse-icon');
                if (content && content.style.display === 'none') {
                    content.style.display = 'block';
                    if (icon) icon.style.transform = 'rotate(0deg)';
                }
            }
        });
    });

    init();
});
