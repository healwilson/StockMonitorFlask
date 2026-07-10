// main.js
// 全局变量
let pollInterval = 5000; // 5秒轮询一次
let timerId = null;
let intradayChart = null;
let fiveDayChart = null;
let stock1Chart = null;
let stock2Chart = null;
let currentPairId = null;
let pairList = [];

// 初始化应用
function initApp() {
    fetchPairs();           // 先获取套利对列表
    setupEventListeners();
    initCharts();
}

// 获取所有套利对
function fetchPairs() {
    fetch('/api/pairs', {
        headers: Auth.withAuthHeader()
    })
    .then(response => Auth.handleResponse(response))
    .then(data => {
        if (!data) return;

        let rawPairs = data.pairs || [];
        if (rawPairs.length > 0 && typeof rawPairs[0] === 'string') {
            rawPairs = rawPairs.map(id => ({ id: id, note: '' }));
        }

        const newActive = data.active;

        // 防抖：只有在新 active 有效且确实改变时才切换
        if (newActive && newActive !== currentPairId && rawPairs.some(p => p.id === newActive)) {
            currentPairId = newActive;
        } else if (!currentPairId && rawPairs.length > 0) {
            // 如果当前没有选中任何 pair，则自动选择第一个
            currentPairId = rawPairs[0].id;
        }
        // 如果 newActive 无效（比如空字符串），则不切换，保持当前选择

        pairList = rawPairs;
        renderPairTabs();

        if (currentPairId) {
            startPolling();
        } else {
            document.getElementById('pairTabsContainer').innerHTML =
                '<div style="text-align:center;color:#999;padding:20px;">暂无套利对，请点击“+ 新建套利对”添加</div>';
        }
    })
    .catch(error => {
        console.error('Error fetching pairs:', error);
        document.getElementById('pairTabsContainer').innerHTML =
            '<div style="text-align:center;color:red;padding:20px;">加载套利对失败，请检查网络或登录状态</div>';
    });
}

// 渲染标签栏
function renderPairTabs() {
    const container = document.getElementById('pairTabsContainer');
    if (!container) return;
    container.innerHTML = '';

    pairList.forEach(pair => {
        const pid = pair.id;
        const noteKey = `pair_note_${pid}`;
        const localNote = localStorage.getItem(noteKey);
        const note = localNote || pair.note || '';

        const tab = document.createElement('div');
        tab.className = `pair-tab ${pid === currentPairId ? 'active' : ''}`;
        tab.dataset.pairId = pid;

        const parts = pid.split('-');
        const short1 = parts[0].replace(/^(sh|sz)/, '');
        const short2 = parts[1].replace(/^(sh|sz)/, '');
        const displayText = note || `${short1} vs ${short2}`;

        const textSpan = document.createElement('span');
        textSpan.textContent = displayText;

        // 编辑按钮
        const editBtn = document.createElement('span');
        editBtn.textContent = '✎';
        editBtn.className = 'edit-note';
        editBtn.title = '编辑备注';
        editBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const newNote = prompt('请输入该套利对的备注：', note);
            if (newNote !== null) {
                localStorage.setItem(noteKey, newNote.trim());
                renderPairTabs();
            }
        });

        // 删除按钮
        const delBtn = document.createElement('span');
        delBtn.textContent = '×';
        delBtn.className = 'delete-pair';
        delBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            removePair(pid);
        });

        tab.appendChild(textSpan);
        tab.appendChild(editBtn);
        tab.appendChild(delBtn);
        tab.addEventListener('click', () => switchPair(pid));

        container.appendChild(tab);
    });
}

// 切换套利对
function switchPair(pid) {
    if (pid === currentPairId) return;
    fetch('/api/switch-pair', {
        method: 'POST',
        headers: Auth.withAuthHeader({'Content-Type': 'application/json'}),
        body: JSON.stringify({pair_id: pid})
    })
    .then(response => Auth.handleResponse(response))
    .then(() => {
        currentPairId = pid;
        renderPairTabs();
        fetchData(); // 立即刷新数据
    })
    .catch(error => console.error('Switch pair failed:', error));
}

// 删除套利对
function removePair(pid) {
    if (!confirm(`确定删除套利对 "${pid}" 吗？`)) return;
    fetch('/api/remove-pair', {
        method: 'POST',
        headers: Auth.withAuthHeader({'Content-Type': 'application/json'}),
        body: JSON.stringify({pair_id: pid})
    })
    .then(response => Auth.handleResponse(response))
    .then(() => {
        localStorage.removeItem(`pair_note_${pid}`);
        fetchPairs();
    })
    .catch(error => console.error('Remove pair failed:', error));
}

// 设置事件监听器
function setupEventListeners() {
    // 添加套利对按钮
    document.getElementById('addPairBtn').addEventListener('click', () => {
        document.getElementById('addPairSection').style.display = 'block';
    });
    document.getElementById('confirmAddPair').addEventListener('click', () => {
        const code1 = document.getElementById('newStock1').value.trim();
        const code2 = document.getElementById('newStock2').value.trim();
        if (!code1 || !code2) {
            alert('请输入两个股票代码');
            return;
        }
        fetch('/api/add-pair', {
            method: 'POST',
            headers: Auth.withAuthHeader({'Content-Type': 'application/json'}),
            body: JSON.stringify({stock1: code1, stock2: code2})
        })
        .then(response => Auth.handleResponse(response))
        .then(() => {
            document.getElementById('addPairSection').style.display = 'none';
            document.getElementById('newStock1').value = '';
            document.getElementById('newStock2').value = '';
            fetchPairs();
        })
        .catch(error => alert('添加失败: ' + error.message));
    });
    document.getElementById('cancelAddPair').addEventListener('click', () => {
        document.getElementById('addPairSection').style.display = 'none';
    });
}

// 开始轮询
function startPolling() {
    if (timerId) {
        clearInterval(timerId);
    }
    timerId = setInterval(fetchData, pollInterval);
    fetchData(); // 立即获取一次
}

// 停止轮询
function stopPolling() {
    if (timerId) {
        clearInterval(timerId);
        timerId = null;
    }
}

// 获取数据（带上当前 pair）
function fetchData() {
    let url = '/api/get-data';
    if (currentPairId) {
        url += `?pair=${encodeURIComponent(currentPairId)}`;
    }
    fetch(url, {
        headers: Auth.withAuthHeader()
    })
    .then(response => Auth.handleResponse(response))
    .then(data => {
        if (data) {
            updateUI(data);
        }
    })
    .catch(error => {
        console.error('Error fetching data:', error);
    });
}

// 更新所有 UI
function updateUI(data) {
    updateStockDisplay('stock1', data.stock1);
    updateStockDisplay('stock2', data.stock2);

    // 更新指数
    updateIndexDisplay('sh000001', data.index1);
    updateIndexDisplay('sz399001', data.index2);
    updateIndexDisplay('sz399006', data.index3);
    updateIndexDisplay('sh000688', data.index4);
    updateIndexDisplay('sh000016', data.index5);
    updateIndexDisplay('sh000300', data.index6);
    updateIndexDisplay('sh000905', data.index7);
    updateIndexDisplay('sh000852', data.index8);

    // 更新股票走势图
    updateStockChart('stock1', data.stock1ChartData, data.stock1);
    updateStockChart('stock2', data.stock2ChartData, data.stock2);

    // 更新价差图表
    updateIntradayChart(data.intraday);
    updateFiveDayChart(data.fiveDay);

    // 更新统计信息
    updateStatsDisplay(data);
}

// 更新指数显示
function updateIndexDisplay(indexCode, indexData) {
    const item = document.querySelector(`.index-item[data-code="${indexCode}"]`);
    if (!item) return;

    const indexName = item.querySelector('.index-name');
    const indexPrice = item.querySelector('.index-price');
    const indexChange = item.querySelector('.index-change');

    if (indexData) {
        indexName.textContent = indexData.name || indexCode;
        indexPrice.textContent = indexData.price?.toFixed(2) || '--';

        const changePercent = indexData.changePercent || 0;
        const changeText = `${changePercent >= 0 ? '+' : ''}${(changePercent * 100).toFixed(2)}%`;
        indexChange.textContent = changeText;

        indexChange.className = `index-change ${changePercent >= 0 ? 'positive' : 'negative'}`;

        const intensity = Math.min(0.2, Math.abs(changePercent) * 2);
        if (changePercent > 0) {
            item.style.backgroundColor = `rgba(245,108,108,${intensity})`;
        } else if (changePercent < 0) {
            item.style.backgroundColor = `rgba(103,194,58,${intensity})`;
        } else {
            item.style.backgroundColor = '#f8f9fa';
        }
    }
}

// 更新股票显示
function updateStockDisplay(id, stockData) {
    const nameEl = document.getElementById(`${id}-name`);
    const priceEl = document.getElementById(`${id}-price`);
    const changeEl = document.getElementById(`${id}-change`);

    if (!stockData || !stockData.code) {
        nameEl.textContent = `${id.toUpperCase()}: 未设置`;
        priceEl.textContent = '¥--';
        changeEl.textContent = '--%';
        return;
    }

    nameEl.textContent = `${stockData.name} (${stockData.code})`;
    nameEl.style.color = '#2c3e50';
    priceEl.textContent = `¥${stockData.price.toFixed(2)}`;

    const changePercent = stockData.changePercent || 0;
    const changeText = `${changePercent >= 0 ? '+' : ''}${(changePercent * 100).toFixed(2)}%`;
    changeEl.textContent = changeText;
    changeEl.className = changePercent >= 0 ? 'positive' : 'negative';
}

// 初始化图表
function initCharts() {
    stock1Chart = echarts.init(document.getElementById('stock1-chart'));
    stock2Chart = echarts.init(document.getElementById('stock2-chart'));

    const stockChartOption = {
        grid: { top: 5, bottom: 5, left: 5, right: 5, containLabel: false },
        xAxis: { type: 'category', boundaryGap: false, show: false },
        yAxis: {
            type: 'value', scale: true, splitLine: { show: false }, show: false,
            axisLine: { show: true },
            axisLabel: { show: true, formatter: function(value) { return value.toFixed(2) + '%'; } }
        },
        series: [{
            type: 'line', smooth: true, symbol: 'none',
            lineStyle: { width: 2 },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(58,77,233,0.8)' },
                    { offset: 1, color: 'rgba(58,77,233,0.1)' }
                ])
            },
            data: []
        }],
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return `时间: ${params[0].name}<br/>涨跌幅: ${params[0].value.toFixed(2)}%`;
            },
            position: function(pos, params, dom, rect, size) { return [pos[0], '10%']; },
            backgroundColor: 'rgba(50,50,50,0.7)', borderWidth: 0,
            textStyle: { color: '#fff' }
        }
    };
    stock1Chart.setOption(stockChartOption);
    stock2Chart.setOption(stockChartOption);

    intradayChart = echarts.init(document.getElementById('intradayChart'));
    intradayChart.setOption({
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return `时间: ${params[0].name}<br/>价差: ${(params[0].value * 100).toFixed(2)}%`;
            }
        },
        grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
        xAxis: {
            type: 'category', data: [], axisTick: {show:false}, axisLine: {show:false},
            axisLabel: {
                rotate: 0, interval: 0,
                formatter: function(value) {
                    if (['09:30','10:00','10:30','11:00','11:30','13:30','14:00','14:30','15:00'].includes(value)) {
                        return value === '11:30' ? '11:30/13:00' : value;
                    }
                    return '';
                }
            }
        },
        yAxis: {
            type: 'value', name: '价差 (%)',
            axisLabel: { formatter: function(value) { return (value * 100).toFixed(2) + '%'; } }
        },
        series: [{
            name: '价差', type: 'line', smooth: true, data: [],
            lineStyle: { width: 3, color: '#66ccff' },
            itemStyle: { color: '#66ccff' },
            markLine: {
                silent: true,
                data: [{ yAxis: 0, lineStyle: { color: '#999', type: 'dashed' } }]
            }
        }]
    });

    fiveDayChart = echarts.init(document.getElementById('fiveDayChart'));
    fiveDayChart.setOption({
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return `时间: ${params[0].name}<br/>价差: ${(params[0].value * 100).toFixed(2)}%`;
            }
        },
        grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
        xAxis: { type: 'category', axisLabel: { rotate: 0, formatter: function(value) { return ''; } } },
        yAxis: {
            type: 'value', name: '价差 (%)',
            axisLabel: { show: true, formatter: function(value) { return (value * 100).toFixed(2) + '%'; } },
            axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false }
        },
        series: [{
            symbol: 'none', name: '价差', type: 'line', data: [],
            lineStyle: { width: 2, color: '#66ccff' },
            itemStyle: { color: '#66ccff' },
            markLine: {
                silent: true, symbol: 'none',
                lineStyle: { color: '#999', type: 'dashed', width: 1.5 },
                data: []
            }
        }]
    });
}

// 更新股票走势图
function updateStockChart(stockId, chartData, stockData) {
    const chart = stockId === 'stock1' ? stock1Chart : stock2Chart;
    if (!chart || !chartData || !chartData.prices || chartData.prices.length === 0) return;

    let changePercentData = [];
    if (chartData.change_percent && chartData.change_percent.length === chartData.prices.length) {
        changePercentData = chartData.change_percent.map(p => p * 100);
    } else {
        if (chartData.prices.length > 0) {
            const basePrice = chartData.prices[0];
            changePercentData = chartData.prices.map(price => {
                return (price && basePrice) ? ((price - basePrice) / basePrice * 100) : 0;
            });
        }
    }

    const lastValue = changePercentData.length > 0 ? changePercentData[changePercentData.length - 1] : 0;
    const isPositive = lastValue >= 0;
    const color = isPositive ? '#f56c6c' : '#67c23a';

    chart.setOption({
        xAxis: { data: chartData.times || [] },
        yAxis: {
            axisLabel: { formatter: function(value) { return value.toFixed(2) + '%'; } }
        },
        series: [{
            name: '分时走势', type: 'line', data: changePercentData,
            smooth: true, symbol: 'none',
            lineStyle: { width: 2, color: color },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: isPositive ? 'rgba(245,108,108,0.5)' : 'rgba(103,194,58,0.5)' },
                    { offset: 1, color: isPositive ? 'rgba(245,108,108,0.1)' : 'rgba(103,194,58,0.1)' }
                ])
            }
        }]
    });
}

// 更新当日价差图表
function updateIntradayChart(intradayData) {
    if (!intradayChart || !intradayData || !intradayData.data) return;
    const dataPoints = intradayData.data;
    const filteredData = dataPoints.filter(d => {
        const time = d.time;
        const hour = parseInt(time.split(':')[0]);
        const minute = parseInt(time.split(':')[1]);
        return (hour >= 9 && minute >= 30) || hour >= 10;
    });
    const times = filteredData.map(d => d.time);
    const values = filteredData.map(d => d.value);
    const lunchTimeIndex = times.findIndex(time => time === '11:30');
    const markLines = [];
    if (lunchTimeIndex !== -1) {
        markLines.push({
            xAxis: lunchTimeIndex,
            lineStyle: { color: '#999', type: 'dashed', width: 1.5 },
            label: { show: false }, symbol: 'none', symbolSize: 0
        });
    }
    intradayChart.setOption({
        xAxis: { data: times, axisLine: { show: false } },
        series: [{
            data: values,
            markLine: {
                symbol: 'none', symbolSize: 0,
                data: [
                    { yAxis: 0, lineStyle: { color: '#999', type: 'dashed', width: 1.5 }, label: { show: false }, symbol: 'none', symbolSize: 0 },
                    ...markLines
                ]
            }
        }]
    });
}

// 更新五日价差图表
function updateFiveDayChart(fiveDayData) {
    if (!fiveDayChart || !fiveDayData || !fiveDayData.data) return;
    const dataPoints = fiveDayData.data;
    const xAxisData = dataPoints.map(d => d.datetime);
    const values = dataPoints.map(d => d.value);
    const datePositions = {};
    let currentDate = '';
    let startIndex = 0;
    for (let i = 0; i < dataPoints.length; i++) {
        const [datePart] = dataPoints[i].datetime.split(' ');
        if (datePart !== currentDate) {
            if (currentDate !== '') {
                const endIndex = i - 1;
                const midIndex = Math.floor((startIndex + endIndex) / 2);
                datePositions[midIndex] = currentDate;
            }
            currentDate = datePart;
            startIndex = i;
        }
    }
    if (currentDate !== '') {
        const endIndex = dataPoints.length - 1;
        const midIndex = Math.floor((startIndex + endIndex) / 2);
        datePositions[midIndex] = currentDate;
    }
    const labels = xAxisData.map((_, index) => datePositions[index] || '');
    const uniqueDates = [...new Set(dataPoints.map(d => d.datetime.split(' ')[0]))];
    const markLines = [];
    uniqueDates.forEach(date => {
        const firstIndex = dataPoints.findIndex(d => d.datetime.startsWith(date));
        if (firstIndex !== -1) {
            markLines.push({
                xAxis: firstIndex,
                lineStyle: { color: '#999', type: 'dashed', width: 1.5 },
                label: { show: false }
            });
        }
    });
    fiveDayChart.setOption({
        xAxis: {
            data: xAxisData,
            axisLabel: { rotate: 0, interval: 0, formatter: function(value, index) { return labels[index]; } },
            axisTick: { show: false }, axisLine: { show: false }
        },
        yAxis: {
            type: 'value', name: '价差 (%)',
            axisLabel: { show: true, formatter: function(value) { return (value * 100).toFixed(2) + '%'; } },
            axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: true }
        },
        series: [{
            symbol: 'none', data: values,
            markLine: {
                data: [
                    { yAxis: 0, lineStyle: { color: '#999', type: 'dashed', width: 1 }, label: { show: false } },
                    ...markLines
                ]
            }
        }]
    });
}

// 更新统计信息
function updateStatsDisplay(data) {
    updateIntradayStats(data.intraday);
    updateFiveDayStats(data.fiveDay);
}

function updateIntradayStats(intradayData) {
    if (!intradayData || !intradayData.stats) return;
    const stats = intradayData.stats;
    const currentValue = parseFloat(stats.current) || 0;
    const prefixCurrent = currentValue >= 0 ? '+' : '';
    const latestTime = stats.latest_time || stats.current_time || '--:--';
    document.getElementById('intraday-current-value').textContent = `${prefixCurrent}${(currentValue * 100).toFixed(2)}%`;
    document.getElementById('intraday-current-value').className = `stat-value ${currentValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('intraday-current-time').textContent = latestTime;

    const maxValue = parseFloat(stats.max) || 0;
    const prefixMax = maxValue >= 0 ? '+' : '';
    document.getElementById('intraday-max-value').textContent = `${prefixMax}${(maxValue * 100).toFixed(2)}%`;
    document.getElementById('intraday-max-value').className = `stat-value ${maxValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('intraday-max-time').textContent = stats.max_time || '--:--';

    const minValue = parseFloat(stats.min) || 0;
    const prefixMin = minValue >= 0 ? '+' : '';
    document.getElementById('intraday-min-value').textContent = `${prefixMin}${(minValue * 100).toFixed(2)}%`;
    document.getElementById('intraday-min-value').className = `stat-value ${minValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('intraday-min-time').textContent = stats.min_time || '--:--';
}

function updateFiveDayStats(fiveDayData) {
    if (!fiveDayData || !fiveDayData.stats) return;
    const stats = fiveDayData.stats;
    const currentValue = parseFloat(stats.current) || 0;
    const prefixCurrent = currentValue >= 0 ? '+' : '';
    document.getElementById('fiveDay-current-value').textContent = `${prefixCurrent}${(currentValue * 100).toFixed(2)}%`;
    document.getElementById('fiveDay-current-value').className = `stat-value ${currentValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('fiveDay-current-time').textContent = stats.current_date || '--:--';

    const maxValue = parseFloat(stats.max) || 0;
    const prefixMax = maxValue >= 0 ? '+' : '';
    document.getElementById('fiveDay-max-value').textContent = `${prefixMax}${(maxValue * 100).toFixed(2)}%`;
    document.getElementById('fiveDay-max-value').className = `stat-value ${maxValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('fiveDay-max-date').textContent = stats.max_date || '--:--';

    const minValue = parseFloat(stats.min) || 0;
    const prefixMin = minValue >= 0 ? '+' : '';
    document.getElementById('fiveDay-min-value').textContent = `${prefixMin}${(minValue * 100).toFixed(2)}%`;
    document.getElementById('fiveDay-min-value').className = `stat-value ${minValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('fiveDay-min-date').textContent = stats.min_date || '--:--';
}

// 更新时间显示
function updateTime() {
    const now = new Date();
    const timeStr = now.toTimeString().substring(0, 8);
    document.getElementById('updateTime').textContent = timeStr;
}

// 每秒更新一次时间
setInterval(updateTime, 1000);
updateTime();

// 主入口
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/login') return;

    if (!Auth.isAuthenticated()) {
        Auth.redirectToLogin();
        return;
    }

    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', function() {
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
        });
    }

    initApp();
});
