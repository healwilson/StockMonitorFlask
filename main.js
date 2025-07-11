// 全局变量
let pollInterval = 5000; // 5秒轮询一次
let timerId = null;
let config = null;
let intradayChart = null;
let fiveDayChart = null;
let stock1Chart = null;
let stock2Chart = null;

// 初始化应用
function initApp() {
    // 获取配置
    fetchConfig();
    // 设置事件监听器
    setupEventListeners();
    // 初始化图表
    initCharts();
}

// 获取配置
function fetchConfig() {
    fetch('/api/config', {
        headers: Auth.withAuthHeader()
    })
    .then(response => Auth.handleResponse(response))
    .then(data => {
        if (data) {
            config = data;
            updateFormFields();
            startPolling();
        }
    })
    .catch(error => console.error('Error loading config:', error));
}

function updateFormFields() {
    document.getElementById('stock1').value = config.stock1 || '';
    document.getElementById('stock2').value = config.stock2 || '';
}

function setupEventListeners() {
    document.getElementById('saveConfig').addEventListener('click', handleSaveConfig);
}

function handleSaveConfig() {
    const stock1 = document.getElementById('stock1').value.trim();
    const stock2 = document.getElementById('stock2').value.trim();

    fetch('/api/update-stocks', {
        method: 'POST',
        headers: Auth.withAuthHeader({'Content-Type': 'application/json'}),
        body: JSON.stringify({ stock1, stock2 })
    })
    .then(response => Auth.handleResponse(response))
    .then(result => {
        if (result && result.status === 'success') {
            alert('股票代码已更新！');
            config = { stock1, stock2 };
            stopPolling(); // 停止之前的轮询
            startPolling(); // 重启轮询
        }
    })
    .catch(error => alert('保存失败: ' + error.message));
}

function startPolling() {
    if (timerId) {
        clearInterval(timerId);
    }
    timerId = setInterval(fetchData, pollInterval);
    fetchData(); // 立即获取一次
}

function stopPolling() {
    if (timerId) {
        clearInterval(timerId);
        timerId = null;
    }
}

function fetchData() {
    fetch('/api/get-data', {
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

function updateUI(data) {
    // 更新股票名称和价格
    updateStockDisplay('stock1', data.stock1);
    updateStockDisplay('stock2', data.stock2);
    
    // 更新指数显示 - 改为直接传递指数代码
    updateIndexDisplay('sh000001', data.index1);
    updateIndexDisplay('sz399001', data.index2);
    updateIndexDisplay('sz399006', data.index3);
    updateIndexDisplay('sh000688', data.index4);
    updateIndexDisplay('sh000016', data.index5);
    updateIndexDisplay('sh000300', data.index6);
    updateIndexDisplay('sh000905', data.index7);
    updateIndexDisplay('sh000852', data.index8);
    
    // 更新股票走势图 - 使用新的数据结构
    updateStockChart('stock1', data.stock1ChartData, data.stock1);
    updateStockChart('stock2', data.stock2ChartData, data.stock2);

    // 更新图表
    updateIntradayChart(data.intraday);
    updateFiveDayChart(data.fiveDay);

    // 更新统计信息
    updateStatsDisplay(data);
}

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
        
        // 设置涨跌颜色
        indexChange.className = `index-change ${changePercent >= 0 ? 'positive' : 'negative'}`;
        
        // 设置背景色
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

// 修改股票显示逻辑
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

    // 获取当前配置中的股票代码
    const configStock1 = document.getElementById('stock1').value.trim();
    const configStock2 = document.getElementById('stock2').value.trim();
    
    // 检查是否匹配当前配置
    const isCurrent = (id === 'stock1' && stockData.code === configStock1) ||
                     (id === 'stock2' && stockData.code === configStock2);
    
    // 显示股票名称和代码，高亮当前配置的股票
    nameEl.textContent = `${stockData.name} (${stockData.code})`;
    nameEl.style.color = isCurrent ? '#2c3e50' : '#999';
    
    // 只显示当前配置的股票价格
    if (isCurrent) {
        priceEl.textContent = `¥${stockData.price.toFixed(2)}`;
        
        // 更新涨跌幅
        const changePercent = stockData.changePercent || 0;
        const changeText = `${changePercent >= 0 ? '+' : ''}${(changePercent * 100).toFixed(2)}%`;
        changeEl.textContent = changeText;
        
        // 根据涨跌设置颜色
        changeEl.className = changePercent >= 0 ? 'positive' : 'negative';
    } else {
        priceEl.textContent = '¥--';
        changeEl.textContent = '--%';
        changeEl.className = '';
    }
}

function initCharts() {
    // 初始化股票走势图
    stock1Chart = echarts.init(document.getElementById('stock1-chart'));
    stock2Chart = echarts.init(document.getElementById('stock2-chart'));

    // 股票走势图配置
    const stockChartOption = {
        grid: {
            top: 5,
            bottom: 5,
            left: 5,
            right: 5,
            containLabel: false
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            show: false // 隐藏X轴
        },
        yAxis: {
            type: 'value',
            scale: true,
            splitLine: { show: false },
            show: false, // 显示Y轴
            axisLine: { show: true }, // 显示轴线
            axisLabel: {
                show: true, // 显示标签
                formatter: function(value) {
                    return value.toFixed(2) + '%'; // 显示百分比格式
                }
            }
        },
        series: [{
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: {
                width: 2
            },
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
            position: function(pos, params, dom, rect, size) {
                // 固定在顶部
                return [pos[0], '10%'];
            },
            backgroundColor: 'rgba(50,50,50,0.7)',
            borderWidth: 0,
            textStyle: {
                color: '#fff'
            }
        }
    };

    // 应用配置
    stock1Chart.setOption(stockChartOption);
    stock2Chart.setOption(stockChartOption);

    // 初始化日内价差图表
    intradayChart = echarts.init(document.getElementById('intradayChart'));
    intradayChart.setOption({
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return `时间: ${params[0].name}<br/>价差: ${(params[0].value * 100).toFixed(2)}%`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: [],
            axisTick: {show:false},
            axisLine: {show:false},
            axisLabel: {
                rotate: 0,
                interval: 0,
                formatter: function(value) {
                    // 只显示半小时的时间点
                    if (value === '09:30' || value === '10:00' || value === '10:30' || 
                        value === '11:00' || value === '11:30' ||  
                        value === '13:30' || value === '14:00' || value === '14:30' || 
                        value === '15:00') {
                        return value === '11:30' ? '11:30/13:00' : value;
                    }
                    return '';
                }
            }
        },
        yAxis: {
            type: 'value',
            name: '价差 (%)',
            axisLabel: {
                formatter: function(value) {
                    return (value * 100).toFixed(2) + '%';
                }
            }
        },
        series: [{
            name: '价差',
            type: 'line',
            smooth: true,
            data: [],
            lineStyle: {
                width: 3,
                color: '#66ccff'
            },
            itemStyle: {
                color: '#66ccff'
            },
            markLine: {
                silent: true,
                data: [{
                    yAxis: 0,  // 零线
                    lineStyle: {
                        color: '#999',
                        type: 'dashed'
                    }
                }]
            }
        }]
    });

    // 初始化5日价差图表
    fiveDayChart = echarts.init(document.getElementById('fiveDayChart'));
    fiveDayChart.setOption({
        tooltip: {
            trigger: 'axis',
            formatter: function(params) {
                return `时间: ${params[0].name}<br/>价差: ${(params[0].value * 100).toFixed(2)}%`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            axisLabel: {
                rotate: 0,
                formatter: function(value) {
                    return '';
                }
            }
        },
        yAxis: {
            type: 'value',
            name: '价差 (%)',
            axisLabel: {
                show: true,
                formatter: function(value) {
                    return (value * 100).toFixed(2) + '%';
                }
            },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false }
        },
        series: [{
            symbol: 'none', 
            name: '价差',
            type: 'line',
            data: [],
            lineStyle: {
                width: 2,
                color: '#66ccff'
            },
            itemStyle: {
                color: '#66ccff'
            },
            markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: {
                    color: '#999',
                    type: 'dashed',
                    width: 1.5
                },
                data: []
            }
        }]
    });
}

function updateStockChart(stockId, chartData, stockData) {
    const chart = stockId === 'stock1' ? stock1Chart : stock2Chart;
    if (!chart || !chartData || !chartData.prices || chartData.prices.length === 0) return;

    // 确保使用正确的涨跌幅数据
    let changePercentData = [];
    if (chartData.change_percent && chartData.change_percent.length === chartData.prices.length) {
        // 如果后端提供了涨跌幅数据，直接使用并转换为百分比数值
        changePercentData = chartData.change_percent.map(p => p * 100);
    } else {
        // 备用方案：如果后端数据缺失，使用当日第一个价格作为参考点
        console.log(`Computing fallback changePercent for ${stockId}`);
        if (chartData.prices.length > 0) {
            const basePrice = chartData.prices[0]; // 通常是开盘价（但实际应该是昨收价）
            changePercentData = chartData.prices.map(price => {
                return (price && basePrice) ? ((price - basePrice) / basePrice * 100) : 0;
            });
        }
    }

    // 确定当前价格颜色（根据最新价格变化）
    const lastValue = changePercentData.length > 0 ? changePercentData[changePercentData.length - 1] : 0;
    const isPositive = lastValue >= 0;
    const color = isPositive ? '#f56c6c' : '#67c23a'; // 红涨绿跌

    // 更新图表选项
    chart.setOption({
        xAxis: {
            data: chartData.times || []
        },
        yAxis: {
            axisLabel: {
                formatter: function(value) {
                    return value.toFixed(2) + '%'; // 确保显示百分比格式
                }
            }
        },
        series: [{
            name: '分时走势',
            type: 'line',
            data: changePercentData,
            smooth: true,
            symbol: 'none', // 不显示数据点
            lineStyle: {
                width: 2,
                color: color
            },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: isPositive ? 'rgba(245, 108, 108, 0.5)' : 'rgba(103, 194, 58, 0.5)' },
                    { offset: 1, color: isPositive ? 'rgba(245, 108, 108, 0.1)' : 'rgba(103, 194, 58, 0.1)' }
                ])
            }
        }]
    });
}

function updateIntradayChart(intradayData) {
    if (!intradayChart || !intradayData || !intradayData.data) return;

    const dataPoints = intradayData.data;
    
    // 过滤掉9:30之前的数据
    const filteredData = dataPoints.filter(d => {
        const time = d.time;
        const hour = parseInt(time.split(':')[0]);
        const minute = parseInt(time.split(':')[1]);
        return (hour >= 9 && minute >= 30) || hour >= 10;
    });

    const times = filteredData.map(d => d.time);
    const values = filteredData.map(d => d.value);

    // 找到11:30的位置索引
    const lunchTimeIndex = times.findIndex(time => time === '11:30');
    const markLines = [];
    
    if (lunchTimeIndex !== -1) {
        markLines.push({
            xAxis: lunchTimeIndex,
            lineStyle: {
                color: '#999',
                type: 'dashed',
                width: 1.5
            },
            label: { show: false },
            symbol: 'none',
            symbolSize: 0
        });
    }

    intradayChart.setOption({
        xAxis: {
            data: times,
            axisLine: { show: false }
        },
        series: [{
            data: values,
            markLine: {
                symbol: 'none',
                symbolSize: 0,
                data: [
                    {
                        yAxis: 0,  // 零线
                        lineStyle: {
                            color: '#999',
                            type: 'dashed',
                            width: 1.5
                        },
                        label: { show: false },
                        symbol: 'none',
                        symbolSize: 0
                    },
                    ...markLines
                ]
            }
        }]
    });
}

function updateFiveDayChart(fiveDayData) {
    if (!fiveDayChart || !fiveDayData || !fiveDayData.data) return;

    const dataPoints = fiveDayData.data;
    const xAxisData = dataPoints.map(d => d.datetime);
    const values = dataPoints.map(d => d.value);

    // 1. 计算每个交易日的日期标签位置
    const datePositions = {};
    let currentDate = '';
    let startIndex = 0;
    
    // 遍历所有数据点，找出交易日变化点
    for (let i = 0; i < dataPoints.length; i++) {
        const [datePart] = dataPoints[i].datetime.split(' ');
        
        if (datePart !== currentDate) {
            // 处理上一个交易日
            if (currentDate !== '') {
                const endIndex = i - 1;
                const midIndex = Math.floor((startIndex + endIndex) / 2);
                datePositions[midIndex] = currentDate;
            }
            
            // 开始新交易日
            currentDate = datePart;
            startIndex = i;
        }
    }
    
    // 处理最后一个交易日
    if (currentDate !== '') {
        const endIndex = dataPoints.length - 1;
        const midIndex = Math.floor((startIndex + endIndex) / 2);
        datePositions[midIndex] = currentDate;
    }

    // 2. 创建标签数组 - 只在交易日中间位置显示日期
    const labels = xAxisData.map((_, index) => datePositions[index] || '');

    // 3. 添加交易日分割线
    const markLines = [];
    const uniqueDates = [...new Set(dataPoints.map(d => d.datetime.split(' ')[0]))];
    
    uniqueDates.forEach(date => {
        const firstIndex = dataPoints.findIndex(d => d.datetime.startsWith(date));
        if (firstIndex !== -1) {
            markLines.push({
                xAxis: firstIndex,
                lineStyle: {
                    color: '#999',
                    type: 'dashed',
                    width: 1.5
                },
                label: { show: false }
            });
        }
    });

    // 4. 更新图表配置
    fiveDayChart.setOption({
        xAxis: {
            data: xAxisData,
            axisLabel: {
                rotate: 0,
                interval: 0, // 显示所有标签
                formatter: function(value, index) {
                    return labels[index];
                }
            },
            axisTick: { show: false },
            axisLine: { show: false }
        },
        yAxis: {
            type: 'value',
            name: '价差 (%)',
            axisLabel: {
                show: true,
                formatter: function(value) {
                    return (value * 100).toFixed(2) + '%';
                }
            },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: true }
        },
        series: [{
            symbol: 'none',
            data: values,
            markLine: {
                data: [
                    {
                        yAxis: 0,
                        lineStyle: {
                            color: '#999',
                            type: 'dashed',
                            width: 1
                        },
                        label: { show: false }
                    },
                    ...markLines
                ]
            }
        }]
    });
}

function updateStatsDisplay(data) {
    updateIntradayStats(data.intraday);
    updateFiveDayStats(data.fiveDay);
}

function updateIntradayStats(intradayData) {
    if (!intradayData || !intradayData.stats) return;

    const stats = intradayData.stats;
    
    // 当前价差
    const currentValue = parseFloat(stats.current) || 0;
    const prefixCurrent = currentValue >= 0 ? '+' : '';
    const latestTime = stats.latest_time || stats.current_time || '--:--';
    document.getElementById('intraday-current-value').textContent = `${prefixCurrent}${(currentValue * 100).toFixed(2)}%`;
    document.getElementById('intraday-current-value').className = `stat-value ${currentValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('intraday-current-time').textContent = latestTime;

    // 最大价差
    const maxValue = parseFloat(stats.max) || 0;
    const prefixMax = maxValue >= 0 ? '+' : '';
    document.getElementById('intraday-max-value').textContent = `${prefixMax}${(maxValue * 100).toFixed(2)}%`;
    document.getElementById('intraday-max-value').className = `stat-value ${maxValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('intraday-max-time').textContent = stats.max_time || '--:--';

    // 最小价差
    const minValue = parseFloat(stats.min) || 0;
    const prefixMin = minValue >= 0 ? '+' : '';
    document.getElementById('intraday-min-value').textContent = `${prefixMin}${(minValue * 100).toFixed(2)}%`;
    document.getElementById('intraday-min-value').className = `stat-value ${minValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('intraday-min-time').textContent = stats.min_time || '--:--';
}

function updateFiveDayStats(fiveDayData) {
    if (!fiveDayData || !fiveDayData.stats) return;

    const stats = fiveDayData.stats;
    
    // 当前价差
    const currentValue = parseFloat(stats.current) || 0;
    const prefixCurrent = currentValue >= 0 ? '+' : '';
    document.getElementById('fiveDay-current-value').textContent = `${prefixCurrent}${(currentValue * 100).toFixed(2)}%`;
    document.getElementById('fiveDay-current-value').className = `stat-value ${currentValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('fiveDay-current-time').textContent = stats.current_date || '--:--';

    // 最大价差
    const maxValue = parseFloat(stats.max) || 0;
    const prefixMax = maxValue >= 0 ? '+' : '';
    document.getElementById('fiveDay-max-value').textContent = `${prefixMax}${(maxValue * 100).toFixed(2)}%`;
    document.getElementById('fiveDay-max-value').className = `stat-value ${maxValue >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('fiveDay-max-date').textContent = stats.max_date || '--:--';

    // 最小价差
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

// 主入口：DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', function() {
    // 如果是登录页面，不初始化主应用
    if (window.location.pathname === '/login') return;

    // 检查认证状态
    if (!Auth.isAuthenticated()) {
        Auth.redirectToLogin();
        return;
    }

    // 添加登出按钮事件
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', function() {
            // 清除令牌
            localStorage.removeItem('auth_token');
            // 重定向到登录页
            window.location.href = '/login';
        });
    }

    // 正常初始化应用
    initApp();
});
