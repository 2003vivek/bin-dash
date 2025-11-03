// Main JavaScript for dashboard
(function() {
    'use strict';
    
    const $ = id => document.getElementById(id);
    const log = (message) => {
        const logEl = $('log');
        const ts = new Date().toISOString();
        logEl.textContent += `[${ts}] ${message}\n`;
        logEl.scrollTop = logEl.scrollHeight;
    };
    
    // WebSocket connections
    let tickerWs = null;
    let analyticsWs = null;
    let alertsWs = null;
    let running = false;
    let tickBuffer = [];
    let priceData = {};
    let zScoreData = [];
    let spreadData = [];
    let correlationData = [];
    let hedgeRatioData = [];
    
    // Chart instances
    let priceChart = null;
    let zScoreChart = null;
    let spreadChart = null;
    let correlationChart = null;
    let hedgeRatioChart = null;
    
    // Initialize WebSocket connections
    function initWebSockets() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/ticker/`;
        
        log(`Attempting to connect to WebSocket: ${wsUrl}`);
        
        try {
            // Ticker WebSocket
            tickerWs = new WebSocket(wsUrl);
            
            tickerWs.onopen = () => {
                log('✓ WebSocket connected successfully');
                updateStatus(true);
            };
            
            tickerWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'tick') {
                        handleTick(data.data);
                    } else if (data.type === 'status') {
                        log(data.message);
                    } else if (data.type === 'error') {
                        log(`Error: ${data.message}`);
                    }
                } catch (e) {
                    log(`Error parsing WebSocket message: ${e.message}`);
                }
            };
            
            tickerWs.onerror = (error) => {
                log('✗ WebSocket connection error. Make sure you are using Uvicorn server.');
                log('Run: uvicorn binance_analytics.asgi:application --host 0.0.0.0 --port 8000');
                updateStatus(false);
            };
            
            tickerWs.onclose = (event) => {
                const reason = event.code === 1006 ? 'Connection failed. Server may not support WebSockets.' : 
                              event.code === 1000 ? 'Connection closed normally' : 
                              `Connection closed (code: ${event.code})`;
                log(`✗ WebSocket closed: ${reason}`);
                updateStatus(false);
                
                // Attempt to reconnect after 3 seconds if not intentionally closed
                if (event.code !== 1000 && running) {
                    log('Attempting to reconnect in 3 seconds...');
                    setTimeout(() => {
                        if (running) {
                            initWebSockets();
                        }
                    }, 3000);
                }
            };
            
            // Analytics WebSocket
            const analyticsUrl = `${protocol}//${host}/ws/analytics/`;
            analyticsWs = new WebSocket(analyticsUrl);
            
            analyticsWs.onopen = () => {
                log('✓ Analytics WebSocket connected');
            };
            
            analyticsWs.onerror = () => {
                log('✗ Analytics WebSocket connection error');
            };
            
            analyticsWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'analytics') {
                        handleAnalytics(data.data);
                    }
                } catch (e) {
                    console.error('Error parsing analytics message:', e);
                }
            };
            
            // Alerts WebSocket
            const alertsUrl = `${protocol}//${host}/ws/alerts/`;
            alertsWs = new WebSocket(alertsUrl);
            
            alertsWs.onopen = () => {
                log('✓ Alerts WebSocket connected');
            };
            
            alertsWs.onerror = () => {
                log('✗ Alerts WebSocket connection error');
            };
            
            alertsWs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'alert') {
                        handleAlert(data.data);
                    }
                } catch (e) {
                    console.error('Error parsing alert message:', e);
                }
            };
            
        } catch (error) {
            log(`✗ Failed to create WebSocket: ${error.message}`);
            updateStatus(false);
        }
    }
    
    function updateStatus(connected) {
        const statusEl = $('status');
        if (connected) {
            statusEl.textContent = 'Connected';
            statusEl.className = 'status connected';
        } else {
            statusEl.textContent = 'Disconnected';
            statusEl.className = 'status disconnected';
        }
    }
    
    function handleTick(tick) {
        tickBuffer.push(tick);
        $('stats').textContent = `Buffered: ${tickBuffer.length}`;
        
        // Update price data
        if (!priceData[tick.symbol]) {
            priceData[tick.symbol] = {x: [], y: []};
        }
        
        const timestamp = new Date(tick.timestamp);
        priceData[tick.symbol].x.push(timestamp);
        priceData[tick.symbol].y.push(tick.price);
        
        // Keep only last 500 points
        if (priceData[tick.symbol].x.length > 500) {
            priceData[tick.symbol].x.shift();
            priceData[tick.symbol].y.shift();
        }
        
        // Update price chart if symbol is selected
        const selectedSymbol = $('priceChartSymbol').value;
        if (selectedSymbol === tick.symbol) {
            updatePriceChart(selectedSymbol);
        }
        
        // Update analytics periodically
        if (tickBuffer.length % 10 === 0) {
            updateAnalytics(tick.symbol);
        }
    }
    
    function handleAnalytics(data) {
        if (data.type === 'z_score') {
            const zScoreValue = data.value || data.z_score || 0;
            if (typeof zScoreValue === 'number' && !isNaN(zScoreValue)) {
                zScoreData.push({
                    x: new Date(),
                    y: zScoreValue
                });
                
                if (zScoreData.length > 500) {
                    zScoreData.shift();
                }
                
                updateZScoreChart();
            }
        }
    }
    
    function handleAlert(alert) {
        log(`ALERT: ${alert.name} - ${alert.condition} (${alert.value})`);
        displayAlert(alert);
    }
    
    // Start/Stop handlers
    $('start').onclick = () => {
        if (running) return;
        
        const symbols = $('symbols').value.split(',').map(s => s.trim()).filter(Boolean);
        if (!symbols.length) {
            log('No symbols provided');
            return;
        }
        
        if (tickerWs && tickerWs.readyState === WebSocket.OPEN) {
            tickerWs.send(JSON.stringify({
                type: 'start',
                symbols: symbols
            }));
            running = true;
            log(`Started collection for: ${symbols.join(', ')}`);
            
            // Populate symbol selector
            updateSymbolSelector(symbols);
        } else {
            log('WebSocket not connected');
        }
    };
    
    $('stop').onclick = () => {
        if (tickerWs && tickerWs.readyState === WebSocket.OPEN) {
            tickerWs.send(JSON.stringify({
                type: 'stop'
            }));
            running = false;
            log('Stopped collection');
        }
    };
    
    // Chart updates
    function updatePriceChart(symbol) {
        if (!priceData[symbol] || !priceData[symbol].x.length) return;
        
        const prices = priceData[symbol].y;
        const timestamps = priceData[symbol].x;
        const currentPrice = prices[prices.length - 1];
        
        // Create text array for annotations (only show on last point)
        const textArray = new Array(prices.length).fill('');
        textArray[textArray.length - 1] = currentPrice.toFixed(2);
        
        const data = [{
            x: timestamps,
            y: prices,
            type: 'scatter',
            mode: 'lines+text',
            name: symbol,
            line: {color: '#0ea5e9'},
            text: textArray,
            textposition: 'top center',
            textfont: {color: '#0ea5e9', size: 12, weight: 'bold'}
        }];
        
        const layout = {
            title: `${symbol.toUpperCase()} Price - Current: ${currentPrice.toFixed(2)}`,
            plot_bgcolor: '#0b1220',
            paper_bgcolor: '#0f172a',
            font: {color: '#e6edf3'},
            xaxis: {title: 'Time'},
            yaxis: {title: 'Price'},
            margin: {l: 50, r: 20, t: 50, b: 50}
        };
        
        Plotly.newPlot('priceChart', data, layout, {responsive: true});
    }
    
    function updateZScoreChart() {
        if (!zScoreData.length) {
            // Show empty chart with message
            const emptyData = [];
            const emptyLayout = {
                title: 'Z-Score (Mean Reversion)',
                plot_bgcolor: '#0b1220',
                paper_bgcolor: '#0f172a',
                font: {color: '#e6edf3'},
                xaxis: {title: 'Time'},
                yaxis: {title: 'Z-Score', tickformat: '.2f'},
                shapes: [
                    {type: 'line', x0: 0, x1: 1, y0: 2, y1: 2, yref: 'paper', line: {color: '#f85149', dash: 'dash'}},
                    {type: 'line', x0: 0, x1: 1, y0: -2, y1: -2, yref: 'paper', line: {color: '#f85149', dash: 'dash'}}
                ],
                margin: {l: 50, r: 20, t: 40, b: 50},
                annotations: [{
                    text: 'Waiting for data...',
                    showarrow: false,
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.5,
                    y: 0.5,
                    font: {color: '#8b949e', size: 14}
                }]
            };
            Plotly.newPlot('zScoreChart', emptyData, emptyLayout, {responsive: true});
            return;
        }
        
        const zScores = zScoreData.map(d => d.y);
        const timestamps = zScoreData.map(d => d.x);
        const currentZScore = zScores[zScores.length - 1];
        
        // Create text array for annotations (only show on last point)
        const textArray = new Array(zScores.length).fill('');
        textArray[textArray.length - 1] = currentZScore.toFixed(2);
        
        const data = [{
            x: timestamps,
            y: zScores,
            type: 'scatter',
            mode: 'lines+text',
            name: 'Z-Score',
            line: {color: '#3fb950'},
            text: textArray,
            textposition: 'top center',
            textfont: {color: '#3fb950', size: 12, weight: 'bold'}
        }];
        
        const layout = {
            title: `Z-Score (Mean Reversion) - Current: ${currentZScore.toFixed(2)}`,
            plot_bgcolor: '#0b1220',
            paper_bgcolor: '#0f172a',
            font: {color: '#e6edf3'},
            xaxis: {title: 'Time'},
            yaxis: {
                title: 'Z-Score',
                tickformat: '.2f'
            },
            shapes: [
                {type: 'line', x0: 0, x1: 1, y0: 2, y1: 2, yref: 'paper', line: {color: '#f85149', dash: 'dash'}},
                {type: 'line', x0: 0, x1: 1, y0: -2, y1: -2, yref: 'paper', line: {color: '#f85149', dash: 'dash'}}
            ],
            margin: {l: 50, r: 20, t: 50, b: 50}
        };
        
        Plotly.newPlot('zScoreChart', data, layout, {responsive: true});
    }
    
    // Analytics updates via API
    async function updateAnalytics(symbol) {
        try {
            const window = parseInt($('window').value);
            
            // Z-Score
            const zScoreResp = await fetch(`/api/analytics/z_score/?symbol=${symbol}&window=${window}`);
            if (zScoreResp.ok) {
                const zData = await zScoreResp.json();
                const zScoreValue = parseFloat(zData.z_score || zData.data?.z_score || 0);
                if (!isNaN(zScoreValue)) {
                    zScoreData.push({
                        x: new Date(),
                        y: zScoreValue
                    });
                    if (zScoreData.length > 500) zScoreData.shift();
                    updateZScoreChart();
                }
            }
            
            // Price Stats
            const statsResp = await fetch(`/api/analytics/price_stats/?symbol=${symbol}&window=${window}`);
            if (statsResp.ok) {
                const stats = await statsResp.json();
                updatePriceStats(stats);
            }
            
            // Spread (if two symbols)
            const symbols = $('symbols').value.split(',').map(s => s.trim()).filter(Boolean);
            if (symbols.length >= 2) {
                // Pair Spread (price difference between two symbols)
                const spreadResp = await fetch(`/api/analytics/spread/?symbol1=${symbols[0]}&symbol2=${symbols[1]}&window=${window}`);
                if (spreadResp.ok) {
                    const spread = await spreadResp.json();
                    updateSpreadChart(spread, symbols);
                }
                
                // Correlation
                const corrResp = await fetch(`/api/analytics/correlation/?symbol1=${symbols[0]}&symbol2=${symbols[1]}&window=${window}`);
                if (corrResp.ok) {
                    const correlation = await corrResp.json();
                    updateCorrelationChart(correlation);
                }
                
                // Hedge Ratio (OLS Regression) - update less frequently
                if (tickBuffer.length % 20 === 0) {
                    const hedgeResp = await fetch(`/api/analytics/hedge_ratio/?symbol1=${symbols[0]}&symbol2=${symbols[1]}`);
                    if (hedgeResp.ok) {
                        const hedgeRatio = await hedgeResp.json();
                        updateHedgeRatioChart(hedgeRatio, symbols);
                    }
                }
            }
        } catch (error) {
            console.error('Error updating analytics:', error);
        }
    }
    
    function updatePriceStats(stats) {
        const statsEl = $('priceStats');
        statsEl.innerHTML = `
            <div class="stat-item">
                <div class="stat-value">${stats.mean?.toFixed(2) || 'N/A'}</div>
                <div class="stat-label">Mean</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.std?.toFixed(2) || 'N/A'}</div>
                <div class="stat-label">Std Dev</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.min?.toFixed(2) || 'N/A'}</div>
                <div class="stat-label">Min</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.max?.toFixed(2) || 'N/A'}</div>
                <div class="stat-label">Max</div>
            </div>
        `;
    }
    
    function updateSpreadChart(spread, symbols) {
        // Implementation for spread chart (pair spread: price1 - price2)
        if (!spread || (spread.current === undefined && spread.mean === undefined)) {
            // Initialize empty chart
            const emptyData = [{
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                name: 'Pair Spread',
                line: {color: '#d29922'}
            }];
            const emptyLayout = {
                title: 'Pair Spread (Price Difference)',
                plot_bgcolor: '#0b1220',
                paper_bgcolor: '#0f172a',
                font: {color: '#e6edf3'},
                xaxis: {title: 'Time'},
                yaxis: {title: 'Spread', tickformat: '.4f'},
                margin: {l: 50, r: 20, t: 40, b: 50},
                annotations: [{
                    text: 'Requires 2 symbols',
                    showarrow: false,
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.5,
                    y: 0.5,
                    font: {color: '#8b949e', size: 14}
                }]
            };
            Plotly.newPlot('spreadChart', emptyData, emptyLayout, {responsive: true});
            return;
        }
        
        const currentSpread = parseFloat(spread.current || spread.mean || 0);
        
        if (isNaN(currentSpread)) {
            return; // Skip invalid data
        }
        
        spreadData.push({
            x: new Date(),
            y: currentSpread
        });
        
        if (spreadData.length > 500) {
            spreadData.shift();
        }
        
        const spreads = spreadData.map(d => d.y);
        const timestamps = spreadData.map(d => d.x);
        const latestSpread = spreads[spreads.length - 1];
        
        // Create text array for annotations (only show on last point)
        const textArray = new Array(spreads.length).fill('');
        textArray[textArray.length - 1] = latestSpread.toFixed(4);
        
        const symbol1 = symbols && symbols[0] ? symbols[0].toUpperCase() : 'Symbol1';
        const symbol2 = symbols && symbols[1] ? symbols[1].toUpperCase() : 'Symbol2';
        
        const data = [{
            x: timestamps,
            y: spreads,
            type: 'scatter',
            mode: 'lines+text',
            name: `Spread (${symbol1} - ${symbol2})`,
            line: {color: '#d29922'},
            text: textArray,
            textposition: 'top center',
            textfont: {color: '#d29922', size: 12, weight: 'bold'}
        }];
        
        const layout = {
            title: `Pair Spread (${symbol1} - ${symbol2}) - Current: ${latestSpread.toFixed(4)}`,
            plot_bgcolor: '#0b1220',
            paper_bgcolor: '#0f172a',
            font: {color: '#e6edf3'},
            xaxis: {title: 'Time'},
            yaxis: {
                title: `Spread: ${symbol1} Price - ${symbol2} Price`,
                tickformat: '.4f',
                showexponent: 'none'
            },
            margin: {l: 70, r: 20, t: 50, b: 50},
            annotations: [
                {
                    text: `Mean: ${spread.mean?.toFixed(4) || 'N/A'}<br>Std: ${spread.std?.toFixed(4) || 'N/A'}`,
                    showarrow: false,
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.02,
                    y: 0.98,
                    xanchor: 'left',
                    yanchor: 'top',
                    font: {color: '#8b949e', size: 11},
                    bgcolor: 'rgba(15, 23, 42, 0.8)',
                    bordercolor: '#1e293b',
                    borderwidth: 1
                }
            ]
        };
        
        Plotly.newPlot('spreadChart', data, layout, {responsive: true});
    }
    
    function updateHedgeRatioChart(hedgeRatio, symbols) {
        if (!hedgeRatio || hedgeRatio.hedge_ratio === undefined) {
            // Initialize empty chart
            const emptyData = [];
            const emptyLayout = {
                title: 'Hedge Ratio (OLS Regression)',
                plot_bgcolor: '#0b1220',
                paper_bgcolor: '#0f172a',
                font: {color: '#e6edf3'},
                xaxis: {title: 'Time'},
                yaxis: {title: 'Hedge Ratio'},
                margin: {l: 50, r: 20, t: 40, b: 50},
                annotations: [{
                    text: 'Requires 2 symbols',
                    showarrow: false,
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.5,
                    y: 0.5,
                    font: {color: '#8b949e', size: 14}
                }]
            };
            Plotly.newPlot('hedgeRatioChart', emptyData, emptyLayout, {responsive: true});
            return;
        }
        
        const currentHedgeRatio = parseFloat(hedgeRatio.hedge_ratio || 0);
        const rSquared = parseFloat(hedgeRatio.r_squared || 0);
        const alpha = parseFloat(hedgeRatio.alpha || 0);
        
        if (isNaN(currentHedgeRatio)) {
            return;
        }
        
        hedgeRatioData.push({
            x: new Date(),
            y: currentHedgeRatio
        });
        
        if (hedgeRatioData.length > 500) {
            hedgeRatioData.shift();
        }
        
        const ratios = hedgeRatioData.map(d => d.y);
        const timestamps = hedgeRatioData.map(d => d.x);
        const latestRatio = ratios[ratios.length - 1];
        
        // Create text array for annotations
        const textArray = new Array(ratios.length).fill('');
        textArray[textArray.length - 1] = latestRatio.toFixed(4);
        
        const symbol1 = symbols && symbols[0] ? symbols[0].toUpperCase() : 'Symbol1';
        const symbol2 = symbols && symbols[1] ? symbols[1].toUpperCase() : 'Symbol2';
        
        const data = [{
            x: timestamps,
            y: ratios,
            type: 'scatter',
            mode: 'lines+text',
            name: 'Hedge Ratio',
            line: {color: '#8b5cf6'},
            text: textArray,
            textposition: 'top center',
            textfont: {color: '#8b5cf6', size: 12, weight: 'bold'}
        }];
        
        const layout = {
            title: `Hedge Ratio (${symbol1} vs ${symbol2}) - Current: ${latestRatio.toFixed(4)} | R²: ${rSquared.toFixed(3)}`,
            plot_bgcolor: '#0b1220',
            paper_bgcolor: '#0f172a',
            font: {color: '#e6edf3'},
            xaxis: {title: 'Time'},
            yaxis: {
                title: 'Hedge Ratio (β)',
                tickformat: '.4f'
            },
            margin: {l: 50, r: 20, t: 60, b: 50},
            annotations: [
                {
                    text: `α (Intercept): ${alpha.toFixed(4)}<br>R²: ${rSquared.toFixed(3)}`,
                    showarrow: false,
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.02,
                    y: 0.98,
                    xanchor: 'left',
                    yanchor: 'top',
                    font: {color: '#8b949e', size: 11},
                    bgcolor: 'rgba(15, 23, 42, 0.8)',
                    bordercolor: '#1e293b',
                    borderwidth: 1
                }
            ]
        };
        
        Plotly.newPlot('hedgeRatioChart', data, layout, {responsive: true});
    }
    
    function updateCorrelationChart(correlation) {
        if (!correlation || correlation.current === undefined) {
            // Initialize empty chart
            const emptyData = [{
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                name: 'Correlation',
                line: {color: '#0ea5e9'}
            }];
            const emptyLayout = {
                title: 'Rolling Correlation',
                plot_bgcolor: '#0b1220',
                paper_bgcolor: '#0f172a',
                font: {color: '#e6edf3'},
                xaxis: {title: 'Time'},
                yaxis: {title: 'Correlation', tickformat: '.3f', range: [-1, 1]},
                margin: {l: 50, r: 20, t: 40, b: 50},
                annotations: [{
                    text: 'Requires 2 symbols',
                    showarrow: false,
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.5,
                    y: 0.5,
                    font: {color: '#8b949e', size: 14}
                }]
            };
            Plotly.newPlot('correlationChart', emptyData, emptyLayout, {responsive: true});
            return;
        }
        
        const currentCorr = parseFloat(correlation.current || 0);
        
        if (isNaN(currentCorr)) {
            return;
        }
        
        correlationData.push({
            x: new Date(),
            y: currentCorr
        });
        
        if (correlationData.length > 500) {
            correlationData.shift();
        }
        
        const correlations = correlationData.map(d => d.y);
        const timestamps = correlationData.map(d => d.x);
        const latestCorr = correlations[correlations.length - 1];
        
        // Create text array for annotations (only show on last point)
        const textArray = new Array(correlations.length).fill('');
        textArray[textArray.length - 1] = latestCorr.toFixed(3);
        
        const data = [{
            x: timestamps,
            y: correlations,
            type: 'scatter',
            mode: 'lines+text',
            name: 'Correlation',
            line: {color: '#0ea5e9'},
            text: textArray,
            textposition: 'top center',
            textfont: {color: '#0ea5e9', size: 12, weight: 'bold'}
        }];
        
        const layout = {
            title: `Rolling Correlation - Current: ${latestCorr.toFixed(3)}`,
            plot_bgcolor: '#0b1220',
            paper_bgcolor: '#0f172a',
            font: {color: '#e6edf3'},
            xaxis: {title: 'Time'},
            yaxis: {
                title: 'Correlation',
                tickformat: '.3f',
                range: [-1, 1]  // Correlation is between -1 and 1
            },
            shapes: [
                {type: 'line', x0: 0, x1: 1, y0: 0, y1: 0, yref: 'paper', line: {color: '#8b949e', dash: 'dash'}}
            ],
            margin: {l: 50, r: 20, t: 50, b: 50}
        };
        
        Plotly.newPlot('correlationChart', data, layout, {responsive: true});
    }
    
    function updateSymbolSelector(symbols) {
        const selector = $('priceChartSymbol');
        selector.innerHTML = '<option value="">Select Symbol</option>';
        symbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol.toUpperCase();
            selector.appendChild(option);
        });
    }
    
    $('priceChartSymbol').onchange = (e) => {
        const symbol = e.target.value;
        if (symbol && priceData[symbol]) {
            updatePriceChart(symbol);
        }
    };
    
    // Export functionality
    $('export').onclick = async () => {
        try {
            const format = $('exportFormat').value;
            const symbols = $('symbols').value.split(',').map(s => s.trim()).filter(Boolean);
            const symbol = symbols[0] || '';
            
            const response = await fetch('/api/export/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    format: format,
                    symbol: symbol,
                    type: 'ticks'
                })
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${symbol || 'all'}_ticks.${format}`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                log('Data exported');
            }
        } catch (error) {
            log(`Export error: ${error.message}`);
        }
    };
    
    // Upload functionality
    $('uploadFile').onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('timeframe', $('timeframe').value);
            
            const response = await fetch('/api/upload-ohlc/', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                log(`Uploaded: ${result.message}`);
            } else {
                const error = await response.json();
                log(`Upload error: ${error.error}`);
            }
        } catch (error) {
            log(`Upload error: ${error.message}`);
        }
    };
    
    // Alert management
    $('addAlert').onclick = () => {
        const name = prompt('Alert name:');
        const condition = prompt('Condition (e.g., z_score > 2):');
        const symbols = $('symbols').value.split(',').map(s => s.trim()).filter(Boolean);
        
        if (name && condition && symbols.length > 0) {
            createAlert(name, condition, symbols[0]);
        }
    };
    
    async function createAlert(name, condition, symbol) {
        try {
            const response = await fetch('/api/alerts/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    condition: condition,
                    symbol: symbol,
                    is_active: true
                })
            });
            
            if (response.ok) {
                loadAlerts();
                log(`Alert created: ${name}`);
            }
        } catch (error) {
            log(`Error creating alert: ${error.message}`);
        }
    }
    
    async function loadAlerts() {
        try {
            const response = await fetch('/api/alerts/');
            if (response.ok) {
                const alerts = await response.json();
                displayAlerts(alerts);
            }
        } catch (error) {
            console.error('Error loading alerts:', error);
        }
    }
    
    function displayAlerts(alerts) {
        const alertsList = $('alertsList');
        alertsList.innerHTML = '';
        
        alerts.forEach(alert => {
            const alertEl = document.createElement('div');
            alertEl.className = 'alert-item' + (alert.last_triggered ? ' triggered' : '');
            alertEl.innerHTML = `
                <strong>${alert.name}</strong> - ${alert.symbol}<br>
                <small>${alert.condition}</small>
                ${alert.trigger_count > 0 ? `<br><small>Triggered ${alert.trigger_count} times</small>` : ''}
            `;
            alertsList.appendChild(alertEl);
        });
    }
    
    function displayAlert(alert) {
        const alertsList = $('alertsList');
        const alertEl = document.createElement('div');
        alertEl.className = 'alert-item triggered';
        alertEl.innerHTML = `
            <strong>${alert.name}</strong> - ${alert.symbol}<br>
            <small>${alert.condition} = ${alert.value}</small>
            <br><small>${new Date(alert.timestamp).toLocaleString()}</small>
        `;
        alertsList.insertBefore(alertEl, alertsList.firstChild);
    }
    
    // Clear log
    $('clearLog').onclick = () => {
        $('log').textContent = '';
    };
    
    // Initialize charts on page load
    updateZScoreChart();  // Initialize with empty state
    updateSpreadChart(null, []);  // Initialize with placeholder
    updateCorrelationChart(null);  // Initialize with placeholder
    updateHedgeRatioChart(null, []);  // Initialize with placeholder
    
    // Initialize
    // Check if WebSocket is supported
    if ('WebSocket' in window) {
        initWebSockets();
        loadAlerts();
    } else {
        log('✗ WebSocket not supported in this browser');
        updateStatus(false);
    }
    
    // Periodic analytics update
    setInterval(() => {
        if (running) {
            const symbols = $('symbols').value.split(',').map(s => s.trim()).filter(Boolean);
            if (symbols.length > 0) {
                updateAnalytics(symbols[0]);
            }
        }
    }, 5000); // Update every 5 seconds
    
    log('Dashboard initialized');
})();

