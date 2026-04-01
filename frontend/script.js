// Global variables // From varshil09
let charts = {};
let plotlyChart = null;
let distributionChart = null;
let currentDistributionView = 'histogram';

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');

    if (tabName === 'analytics') {
        setTimeout(() => {
            loadStatistics();
            updateChart();
            loadNeighborhoodChart();
            loadYearTrendChart();
            loadQualityChart();
            loadFeatureImportance();
        }, 100);
    }

    if (tabName === 'correlation') {
        setTimeout(() => {
            updateHeatmap();
            loadPriceDistribution();
            updateBoxplot();
            loadCorrelationTable();
        }, 100);
    }

    if (tabName === 'history') {
        setTimeout(() => {
            loadHistory();
            loadHistoryStats();
        }, 100);
    }
}

// Change chart type between 2D and 3D
function changeChartType() {
    const chartType = document.getElementById('chartType').value;
    const controls2D = document.getElementById('controls2D');
    const controls3D = document.getElementById('controls3D');
    const chartTitle = document.getElementById('chartTitle');

    if (chartType === '2d') {
        controls2D.style.display = 'flex';
        controls3D.style.display = 'none';
        chartTitle.innerHTML = '📊 2D Scatter Plot';
    } else {
        controls2D.style.display = 'none';
        controls3D.style.display = 'flex';
        chartTitle.innerHTML = '🎯 3D Scatter Plot';
    }
    updateChart();
}

// Main chart update function
async function updateChart() {
    const chartType = document.getElementById('chartType').value;

    if (chartType === '2d') {
        await render2DScatter();
    } else {
        await render3DScatter();
    }
}

// Render 2D Scatter Plot
async function render2DScatter() {
    const xFeature = document.getElementById('axisX_2d').value;
    const colorFeature = document.getElementById('colorBy_2d').value;

    try {
        const response = await fetch(`http://localhost:5000/api/scatter-data?x=${xFeature}&color=${colorFeature}`);
        const data = await response.json();

        const trace = {
            x: data.x,
            y: data.prices,
            mode: 'markers',
            type: 'scatter',
            marker: {
                size: 8,
                color: data.color_values,
                colorscale: 'Viridis',
                showscale: true,
                colorbar: {
                    title: colorFeature.replace(/([A-Z])/g, ' $1').trim(),
                    thickness: 20
                },
                opacity: 0.7,
                line: {
                    width: 0.5,
                    color: 'rgba(0,0,0,0.3)'
                }
            },
            text: data.hover_text,
            hoverinfo: 'text'
        };

        const layout = {
            title: {
                text: `${xFeature.replace(/([A-Z])/g, ' $1').trim()} vs Sale Price`,
                font: { size: 16 }
            },
            xaxis: {
                title: xFeature.replace(/([A-Z])/g, ' $1').trim(),
                gridcolor: '#e0e0e0',
                zerolinecolor: '#cccccc'
            },
            yaxis: {
                title: 'Sale Price ($)',
                tickformat: '$,.0f',
                gridcolor: '#e0e0e0',
                zerolinecolor: '#cccccc'
            },
            height: 600,
            margin: { l: 70, r: 70, t: 60, b: 50 },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: '#ffffff',
            hovermode: 'closest'
        };

        Plotly.newPlot('plotlyChart', [trace], layout);
        plotlyChart = true;

    } catch (error) {
        console.error('Error rendering 2D scatter:', error);
        showChartError();
    }
}

// Render 3D Scatter Plot
async function render3DScatter() {
    const xFeature = document.getElementById('axisX_3d').value;
    const yFeature = document.getElementById('axisY_3d').value;

    try {
        const response = await fetch(`http://localhost:5000/api/3d-scatter-data?x=${xFeature}&y=${yFeature}`);
        const data = await response.json();

        const trace = {
            x: data.x,
            y: data.y,
            z: data.prices,
            mode: 'markers',
            type: 'scatter3d',
            marker: {
                size: 4,
                color: data.prices,
                colorscale: 'Viridis',
                showscale: true,
                colorbar: {
                    title: 'Sale Price ($)',
                    tickformat: '$,.0f'
                },
                opacity: 0.8,
                line: {
                    width: 0
                }
            },
            text: data.hover_text,
            hoverinfo: 'text'
        };

        const layout = {
            title: {
                text: `3D: ${xFeature.replace(/([A-Z])/g, ' $1').trim()} vs ${yFeature.replace(/([A-Z])/g, ' $1').trim()} vs Price`,
                font: { size: 16 }
            },
            scene: {
                xaxis: {
                    title: xFeature.replace(/([A-Z])/g, ' $1').trim(),
                    gridcolor: '#e0e0e0',
                    gridwidth: 1
                },
                yaxis: {
                    title: yFeature.replace(/([A-Z])/g, ' $1').trim(),
                    gridcolor: '#e0e0e0',
                    gridwidth: 1
                },
                zaxis: {
                    title: 'Sale Price ($)',
                    tickformat: '$,.0f',
                    gridcolor: '#e0e0e0',
                    gridwidth: 1
                },
                camera: {
                    eye: { x: 1.5, y: 1.5, z: 1.5 }
                }
            },
            height: 600,
            margin: { l: 0, r: 0, b: 0, t: 60 },
            paper_bgcolor: '#ffffff'
        };

        Plotly.newPlot('plotlyChart', [trace], layout);
        plotlyChart = true;

    } catch (error) {
        console.error('Error rendering 3D scatter:', error);
        showChartError();
    }
}

function showChartError() {
    const container = document.getElementById('plotlyChart');
    if (container) {
        container.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f8f9fa; border-radius: 12px;">
                <div style="text-align: center;">
                    <p style="color: #c0392b; font-size: 18px;">⚠️ Could not load chart data</p>
                    <p style="color: #666;">Make sure Flask backend is running on port 5000</p>
                    <p style="color: #666; font-size: 12px;">Run: python app.py</p>
                </div>
            </div>
        `;
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch('http://localhost:5000/api/statistics');
        const data = await response.json();

        document.getElementById('avg-price').textContent = `$${data.mean_price.toLocaleString()}`;
        document.getElementById('median-price').textContent = `$${data.median_price.toLocaleString()}`;
        document.getElementById('price-range').textContent = `$${data.min_price.toLocaleString()} - $${data.max_price.toLocaleString()}`;
        document.getElementById('total-houses').textContent = data.total_houses.toLocaleString();
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load neighborhood chart
async function loadNeighborhoodChart() {
    try {
        const response = await fetch('http://localhost:5000/api/price-by-neighborhood');
        const data = await response.json();

        const ctx = document.getElementById('neighborhoodChart').getContext('2d');

        const topNeighborhoods = data.neighborhoods.slice(0, 10);
        const topPrices = data.means.slice(0, 10);

        if (charts.neighborhoodChart) charts.neighborhoodChart.destroy();

        charts.neighborhoodChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: topNeighborhoods,
                datasets: [{
                    label: 'Average Price',
                    data: topPrices,
                    backgroundColor: 'rgba(153, 102, 255, 0.7)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `$${ctx.raw.toLocaleString()}`
                        }
                    }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Price ($)' },
                        ticks: { callback: (val) => `$${val.toLocaleString()}` }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading neighborhood chart:', error);
    }
}

// Load year trend chart
async function loadYearTrendChart() {
    try {
        const response = await fetch('http://localhost:5000/api/price-over-time');
        const data = await response.json();

        const ctx = document.getElementById('yearTrendChart').getContext('2d');

        if (charts.yearTrendChart) charts.yearTrendChart.destroy();

        charts.yearTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.years,
                datasets: [
                    {
                        label: 'Average Price',
                        data: data.means,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Median Price',
                        data: data.medians,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `$${ctx.raw.toLocaleString()}`
                        }
                    }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Price ($)' },
                        ticks: { callback: (val) => `$${val.toLocaleString()}` }
                    },
                    x: { title: { display: true, text: 'Year Built' } }
                }
            }
        });
    } catch (error) {
        console.error('Error loading year trend chart:', error);
    }
}

// Load quality chart
async function loadQualityChart() {
    try {
        const response = await fetch('http://localhost:5000/api/price-by-quality');
        const data = await response.json();

        const ctx = document.getElementById('qualityChart').getContext('2d');

        if (charts.qualityChart) charts.qualityChart.destroy();

        charts.qualityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.qualities,
                datasets: [
                    {
                        label: 'Average Price',
                        data: data.means,
                        backgroundColor: 'rgba(255, 99, 132, 0.7)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Number of Houses',
                        data: data.counts,
                        type: 'line',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                if (context.dataset.label === 'Average Price') {
                                    return `$${context.raw.toLocaleString()}`;
                                }
                                return `${context.raw} houses`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Price ($)' },
                        ticks: { callback: (val) => `$${val.toLocaleString()}` }
                    },
                    y1: {
                        position: 'right',
                        title: { display: true, text: 'Count' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading quality chart:', error);
    }
}

// Load feature importance
async function loadFeatureImportance() {
    try {
        const response = await fetch('http://localhost:5000/api/feature-importance');
        const data = await response.json();

        const ctx = document.getElementById('featureImportanceChart').getContext('2d');

        if (charts.featureImportanceChart) charts.featureImportanceChart.destroy();

        charts.featureImportanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.features.slice(0, 15),
                datasets: [{
                    label: 'Importance Score',
                    data: data.importance.slice(0, 15),
                    backgroundColor: 'rgba(255, 159, 64, 0.7)',
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ctx.raw.toFixed(4)
                        }
                    }
                },
                scales: {
                    x: { title: { display: true, text: 'Importance' } }
                }
            }
        });
    } catch (error) {
        console.error('Error loading feature importance:', error);
    }
}

// Update heatmap
async function updateHeatmap() {
    try {
        const response = await fetch('http://localhost:5000/api/correlation-matrix');
        const data = await response.json();

        const featureCount = document.getElementById('featureCount').value;
        const colorScheme = document.getElementById('colorScheme').value;

        let features = [...data.features];
        let matrix = data.matrix.map(row => [...row]);

        if (featureCount !== 'all') {
            const count = parseInt(featureCount);
            const salePriceIndex = features.indexOf('SalePrice');
            const correlations = matrix.map(row => Math.abs(row[salePriceIndex]));
            const indices = correlations.map((_, i) => i).sort((a, b) => correlations[b] - correlations[a]);
            const topIndices = indices.slice(0, count);
            features = topIndices.map(i => features[i]);
            matrix = topIndices.map(i => topIndices.map(j => data.matrix[i][j]));
        }

        const heatmapTrace = {
            z: matrix,
            x: features,
            y: features,
            type: 'heatmap',
            colorscale: colorScheme,
            showscale: true,
            zmin: -1,
            zmax: 1,
            text: matrix.map(row => row.map(val => val.toFixed(2))),
            texttemplate: '%{text}',
            textfont: { size: 10 },
            hoverongaps: false
        };

        const layout = {
            title: 'Feature Correlation Matrix',
            xaxis: { title: 'Features', tickangle: -45, tickfont: { size: 10 } },
            yaxis: { title: 'Features', tickfont: { size: 10 } },
            height: 800,
            width: Math.max(800, features.length * 35),
            margin: { l: 120, r: 20, t: 60, b: 120 }
        };

        Plotly.newPlot('correlationHeatmap', [heatmapTrace], layout);
    } catch (error) {
        console.error('Error updating heatmap:', error);
    }
}

// Load correlation table
async function loadCorrelationTable() {
    try {
        const response = await fetch('http://localhost:5000/api/feature-correlation');
        const data = await response.json();

        let html = '<table class="data-table"><thead><tr><th>Feature</th>';
        data.features.forEach(f => {
            html += `<th>${f}</th>`;
        });
        html += '</tr></thead><tbody>';

        for (let i = 0; i < data.features.length; i++) {
            html += `<tr><td><strong>${data.features[i]}</strong></td>`;
            for (let j = 0; j < data.matrix[i].length; j++) {
                const value = data.matrix[i][j];
                let colorClass = '';
                if (Math.abs(value) > 0.7) colorClass = 'corr-high';
                else if (Math.abs(value) > 0.4) colorClass = 'corr-medium';
                else if (Math.abs(value) > 0.2) colorClass = 'corr-low';
                html += `<td class="${colorClass}">${value.toFixed(2)}</td>`;
            }
            html += '</tr>';
        }
        html += '</tbody></table>';

        document.getElementById('correlationTable').innerHTML = html;
    } catch (error) {
        console.error('Error loading correlation table:', error);
    }
}

// Change distribution view type
function changeDistributionView(view) {
    currentDistributionView = view;

    // Update active button styling
    document.querySelectorAll('.dist-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    loadPriceDistribution();
}

// Improved Price Distribution Function
async function loadPriceDistribution() {
    try {
        const response = await fetch('http://localhost:5000/api/price-distribution');
        const data = await response.json();

        const prices = data.prices;

        // Calculate statistics
        const mean = prices.reduce((a, b) => a + b, 0) / prices.length;
        const median = [...prices].sort((a, b) => a - b)[Math.floor(prices.length / 2)];
        const stdDev = Math.sqrt(prices.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / prices.length);

        // Create histogram bins
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const binCount = 30;
        const binWidth = (maxPrice - minPrice) / binCount;

        const bins = Array(binCount).fill(0);
        const binEdges = [];

        for (let i = 0; i <= binCount; i++) {
            binEdges.push(minPrice + i * binWidth);
        }

        prices.forEach(price => {
            const binIndex = Math.min(Math.floor((price - minPrice) / binWidth), binCount - 1);
            bins[binIndex]++;
        });

        const binCenters = [];
        for (let i = 0; i < binCount; i++) {
            binCenters.push(minPrice + (i + 0.5) * binWidth);
        }

        // Create trace based on view type
        let trace;

        if (currentDistributionView === 'histogram') {
            trace = {
                x: binCenters,
                y: bins,
                type: 'bar',
                name: 'Frequency',
                marker: {
                    color: 'rgba(54, 162, 235, 0.7)',
                    line: {
                        color: 'rgba(54, 162, 235, 1)',
                        width: 1
                    }
                },
                hovertemplate: 'Price: $%{x:,.0f}<br>Houses: %{y}<extra></extra>'
            };
        } else if (currentDistributionView === 'density') {
            // Calculate density
            const total = prices.length;
            const density = bins.map(count => (count / total) / binWidth * 1000000);

            trace = {
                x: binCenters,
                y: density,
                type: 'scatter',
                mode: 'lines+fill',
                name: 'Density',
                fill: 'tozeroy',
                line: {
                    color: 'rgba(75, 192, 192, 1)',
                    width: 2
                },
                fillcolor: 'rgba(75, 192, 192, 0.3)',
                hovertemplate: 'Price: $%{x:,.0f}<br>Density: %{y:.2f}<extra></extra>'
            };
        } else {
            // Cumulative distribution
            const total = prices.length;
            const cumulative = [];
            for (let i = 0; i <= binCount; i++) {
                const threshold = minPrice + i * binWidth;
                const countBelow = prices.filter(p => p <= threshold).length;
                cumulative.push((countBelow / total) * 100);
            }

            trace = {
                x: binEdges,
                y: cumulative,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Cumulative %',
                line: {
                    color: 'rgba(153, 102, 255, 1)',
                    width: 2
                },
                marker: {
                    size: 4,
                    color: 'rgba(153, 102, 255, 1)'
                },
                fill: 'tozeroy',
                fillcolor: 'rgba(153, 102, 255, 0.2)',
                hovertemplate: 'Price: $%{x:,.0f}<br>Cumulative: %{y:.1f}%<extra></extra>'
            };
        }

        const layout = {
            title: {
                text: currentDistributionView === 'histogram' ? 'House Price Distribution' :
                    currentDistributionView === 'density' ? 'Price Density Distribution' :
                        'Cumulative Price Distribution',
                font: { size: 14, family: 'Segoe UI' }
            },
            xaxis: {
                title: 'Sale Price ($)',
                tickformat: '$,.0f',
                gridcolor: '#e0e0e0',
                zerolinecolor: '#cccccc'
            },
            yaxis: {
                title: currentDistributionView === 'histogram' ? 'Number of Houses' :
                    currentDistributionView === 'density' ? 'Density (per million $)' :
                        'Cumulative Percentage (%)',
                gridcolor: '#e0e0e0',
                zerolinecolor: '#cccccc'
            },
            height: 450,
            margin: { l: 70, r: 50, t: 60, b: 50 },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: '#ffffff',
            bargap: 0.05,
            showlegend: false
        };

        // Add vertical line for mean and median for histogram and density
        if (currentDistributionView === 'histogram' || currentDistributionView === 'density') {
            const shapes = [
                {
                    type: 'line',
                    x0: mean,
                    x1: mean,
                    y0: 0,
                    y1: 1,
                    yref: 'paper',
                    line: { color: 'red', width: 2, dash: 'dash' },
                    name: 'Mean'
                },
                {
                    type: 'line',
                    x0: median,
                    x1: median,
                    y0: 0,
                    y1: 1,
                    yref: 'paper',
                    line: { color: 'green', width: 2, dash: 'dash' },
                    name: 'Median'
                }
            ];
            layout.shapes = shapes;
        }

        Plotly.newPlot('priceDistributionContainer', [trace], layout);

        // Update statistics display
        const skewness = ((mean - median) / stdDev).toFixed(2);
        const statsHtml = `
            <div class="stats-row">
                <div class="stat-box">
                    <span class="stat-label">Mean Price</span>
                    <span class="stat-value">$${mean.toLocaleString()}</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">Median Price</span>
                    <span class="stat-value">$${median.toLocaleString()}</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">Std Deviation</span>
                    <span class="stat-value">$${stdDev.toLocaleString()}</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">Range</span>
                    <span class="stat-value">$${minPrice.toLocaleString()} - $${maxPrice.toLocaleString()}</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">Skewness</span>
                    <span class="stat-value">${skewness}</span>
                </div>
                <div class="stat-box">
                    <span class="stat-label">Total Houses</span>
                    <span class="stat-value">${prices.length.toLocaleString()}</span>
                </div>
            </div>
        `;
        document.getElementById('price-distribution-stats').innerHTML = statsHtml;

    } catch (error) {
        console.error('Error loading price distribution:', error);
    }
}

// Improved Box Plot Function
async function updateBoxplot() {
    try {
        const sortBy = document.getElementById('boxplotSortBy').value;
        const topN = parseInt(document.getElementById('boxplotTopN').value);

        const response = await fetch('http://localhost:5000/api/boxplot-data?feature=Neighborhood');
        const data = await response.json();

        // Create data array for sorting
        let neighborhoods = [];
        for (let i = 0; i < data.categories.length; i++) {
            const prices = [...data.data[i]].sort((a, b) => a - b);
            const median = prices[Math.floor(prices.length / 2)];
            const mean = prices.reduce((a, b) => a + b, 0) / prices.length;
            const min = Math.min(...prices);
            const max = Math.max(...prices);
            const q1 = prices[Math.floor(prices.length * 0.25)];
            const q3 = prices[Math.floor(prices.length * 0.75)];

            neighborhoods.push({
                name: data.categories[i],
                prices: data.data[i],
                median: median,
                mean: mean,
                min: min,
                max: max,
                q1: q1,
                q3: q3,
                count: prices.length
            });
        }

        // Sort based on selection
        if (sortBy === 'price') {
            neighborhoods.sort((a, b) => b.median - a.median);
        } else if (sortBy === 'name') {
            neighborhoods.sort((a, b) => a.name.localeCompare(b.name));
        } else if (sortBy === 'count') {
            neighborhoods.sort((a, b) => b.count - a.count);
        }

        // Take top N
        const topNeighborhoods = neighborhoods.slice(0, topN);

        // Prepare data for Plotly
        const traces = [];
        const colors = [
            'rgba(54, 162, 235, 0.7)', 'rgba(255, 99, 132, 0.7)',
            'rgba(75, 192, 192, 0.7)', 'rgba(153, 102, 255, 0.7)',
            'rgba(255, 159, 64, 0.7)', 'rgba(255, 205, 86, 0.7)',
            'rgba(201, 203, 207, 0.7)', 'rgba(54, 162, 235, 0.7)',
            'rgba(255, 99, 132, 0.7)', 'rgba(75, 192, 192, 0.7)',
            'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)'
        ];

        topNeighborhoods.forEach((hood, idx) => {
            const trace = {
                y: hood.prices,
                type: 'box',
                name: hood.name,
                boxmean: 'sd',
                marker: { color: colors[idx % colors.length] },
                line: { width: 2 },
                boxpoints: 'outliers',
                jitter: 0.3,
                pointpos: -1.5,
                hoverinfo: 'y+name',
                hovertemplate: '%{y:$,.0f}<extra></extra>'
            };
            traces.push(trace);
        });

        const layout = {
            title: {
                text: 'Price Distribution by Neighborhood',
                font: { size: 16, family: 'Segoe UI' }
            },
            xaxis: {
                title: 'Neighborhood',
                tickangle: -45,
                tickfont: { size: 11 }
            },
            yaxis: {
                title: 'Sale Price ($)',
                tickformat: '$,.0f',
                gridcolor: '#e0e0e0',
                zerolinecolor: '#cccccc'
            },
            height: 500,
            margin: { l: 80, r: 40, t: 60, b: 100 },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: '#ffffff',
            showlegend: false,
            hovermode: 'closest'
        };

        Plotly.newPlot('boxplotChart', traces, layout);

        // Generate insights
        const bestNeighborhood = topNeighborhoods[0];
        const worstNeighborhood = topNeighborhoods[topNeighborhoods.length - 1];
        const priceGap = ((bestNeighborhood.median - worstNeighborhood.median) / worstNeighborhood.median * 100).toFixed(0);
        const mostHouses = topNeighborhoods.reduce((max, h) => h.count > max.count ? h : max, topNeighborhoods[0]);

        const insightsHtml = `
            <div class="boxplot-insights-content">
                <h4>📊 Key Insights</h4>
                <div class="insights-grid-small">
                    <div class="insight-badge">
                        <span class="emoji">🏆</span>
                        <span><strong>Highest Price:</strong> ${bestNeighborhood.name}</span>
                        <span>$${bestNeighborhood.median.toLocaleString()} (median)</span>
                    </div>
                    <div class="insight-badge">
                        <span class="emoji">📉</span>
                        <span><strong>Lowest Price:</strong> ${worstNeighborhood.name}</span>
                        <span>$${worstNeighborhood.median.toLocaleString()} (median)</span>
                    </div>
                    <div class="insight-badge">
                        <span class="emoji">📈</span>
                        <span><strong>Price Gap:</strong> ${priceGap}% difference</span>
                        <span>between top and bottom</span>
                    </div>
                    <div class="insight-badge">
                        <span class="emoji">🏠</span>
                        <span><strong>Most Houses:</strong> ${mostHouses.name}</span>
                        <span>${mostHouses.count} properties</span>
                    </div>
                </div>
                <div class="insight-note">
                    💡 <strong>Investment Tip:</strong> ${bestNeighborhood.name} shows the highest median price. 
                    Look for properties with Overall Quality ≥ 7 in this area for best ROI potential.
                </div>
            </div>
        `;

        document.getElementById('boxplot-insights').innerHTML = insightsHtml;

    } catch (error) {
        console.error('Error updating boxplot:', error);
    }
}

// Load prediction history
async function loadHistory() {
    try {
        const response = await fetch('http://localhost:5000/api/history');
        const data = await response.json();

        if (data.success) {
            displayHistory(data.history);
        } else {
            console.error('Error loading history:', data.error);
        }
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('history-table-body').innerHTML =
            '<tr><td colspan="6" class="error-text">Failed to load history. Make sure server is running.</td></tr>';
    }
}

// Display history in table
function displayHistory(history) {
    const tbody = document.getElementById('history-table-body');

    if (history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-text">No predictions yet. Make a prediction to see it here!</td></tr>';
        return;
    }

    tbody.innerHTML = history.map(item => {
        // Get confidence range values
        // Debug: log the item to see what's available
        console.log('History item:', item);

        // Get confidence range values - handle both possible formats
        let confidenceDisplay = 'N/A';
        if (item.formatted_lower && item.formatted_upper) {
            confidenceDisplay = `${item.formatted_lower} - ${item.formatted_upper}`;
        } else if (item.confidence_lower && item.confidence_upper) {
            confidenceDisplay = `$${item.confidence_lower.toLocaleString()} - $${item.confidence_upper.toLocaleString()}`;
        }

        return `
            <tr>
                <td>${new Date(item.timestamp).toLocaleString()}</td>
                <td class="price-cell">${item.formatted_price || `$${item.predicted_price?.toLocaleString()}`}</td>
                <td>${confidenceDisplay}</td>
                <td>
                    <div class="feature-badges">
                        <span class="badge">🏠 ${item.input_features?.GrLivArea || 0} sqft</span>
                        <span class="badge">⭐ Q${item.input_features?.OverallQual || 0}</span>
                        <span class="badge">📅 ${item.input_features?.YearBuilt || 0}</span>
                        <span class="badge">📍 ${item.input_features?.Neighborhood || 'Unknown'}</span>
                    </div>
                </td>
                <td class="${item.vs_average_percent?.includes('-') ? 'negative' : 'positive'}">
                    ${item.vs_average_diff || 'N/A'} (${item.vs_average_percent || 'N/A'})
                </td>

                <td class="feedback-cell">
                    ${item.is_verified ?
                '<span class="verified-badge">✓ Verified</span>' :
                `<button class="btn-feedback" onclick="showFeedbackModal(${item.id})">📝 Add Actual Price</button>`
            }
                </td>

                <td>
                    <button class="btn-delete" onclick="deletePrediction(${item.id})">🗑️</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Load history statistics
async function loadHistoryStats() {
    try {
        const response = await fetch('http://localhost:5000/api/history/stats');
        const data = await response.json();

        if (data.success) {
            document.getElementById('total-predictions').textContent = data.total_predictions;
            document.getElementById('avg-prediction').textContent = `$${data.avg_prediction.toLocaleString()}`;
            document.getElementById('max-prediction').textContent = `$${data.max_prediction.toLocaleString()}`;
            document.getElementById('min-prediction').textContent = `$${data.min_prediction.toLocaleString()}`;
        }
    } catch (error) {
        console.error('Error loading history stats:', error);
    }
}

// Delete a single prediction
async function deletePrediction(id) {
    if (confirm('Are you sure you want to delete this prediction?')) {
        try {
            const response = await fetch(`http://localhost:5000/api/history/delete/${id}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.success) {
                loadHistory();
                loadHistoryStats();
                showToast('Prediction deleted successfully!');
            } else {
                alert('Error deleting prediction: ' + data.error);
            }
        } catch (error) {
            console.error('Error deleting prediction:', error);
            alert('Failed to delete prediction');
        }
    }
}

// Clear all history
async function clearHistory() {
    if (confirm('⚠️ Are you sure you want to clear ALL prediction history? This action cannot be undone!')) {
        try {
            const response = await fetch('http://localhost:5000/api/history/clear', {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.success) {
                loadHistory();
                loadHistoryStats();
                showToast('All history cleared successfully!');
            } else {
                alert('Error clearing history: ' + data.error);
            }
        } catch (error) {
            console.error('Error clearing history:', error);
            alert('Failed to clear history');
        }
    }
}

// Show toast notification
function showToast(message) {
    let toast = document.querySelector('.toast-notification');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast-notification';
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Prediction form handling
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('predictionForm');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    const priceSpan = document.getElementById('price');
    const rangeSpan = document.getElementById('range');
    const errorMessageSpan = document.getElementById('errorMessage');
    const predictBtn = document.querySelector('.predict-btn');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        resultDiv.style.display = 'none';
        errorDiv.style.display = 'none';

        const formData = {
            GrLivArea: parseInt(document.getElementById('GrLivArea').value),
            LotArea: parseInt(document.getElementById('LotArea').value),
            TotalBsmtSF: parseInt(document.getElementById('TotalBsmtSF').value),
            '1stFlrSF': parseInt(document.getElementById('1stFlrSF').value),
            OverallQual: parseInt(document.getElementById('OverallQual').value),
            OverallCond: parseInt(document.getElementById('OverallCond').value),
            YearBuilt: parseInt(document.getElementById('YearBuilt').value),
            YearRemodAdd: parseInt(document.getElementById('YearRemodAdd').value),
            BedroomAbvGr: parseInt(document.getElementById('BedroomAbvGr').value),
            FullBath: parseInt(document.getElementById('FullBath').value),
            HalfBath: parseInt(document.getElementById('HalfBath').value),
            Fireplaces: parseInt(document.getElementById('Fireplaces').value),
            GarageCars: parseInt(document.getElementById('GarageCars').value),
            GarageArea: parseInt(document.getElementById('GarageArea').value),
            Neighborhood: document.getElementById('Neighborhood').value,
            MSZoning: document.getElementById('MSZoning').value,
            WoodDeckSF: parseInt(document.getElementById('WoodDeckSF').value),
            OpenPorchSF: parseInt(document.getElementById('OpenPorchSF').value)
        };

        formData['2ndFlrSF'] = 0;
        formData['KitchenAbvGr'] = 1;
        formData['TotRmsAbvGrd'] = formData.BedroomAbvGr + formData.FullBath + 3;
        formData['LotFrontage'] = Math.sqrt(formData.LotArea) / 2;

        if (formData.GrLivArea < 300) {
            showError('Living area must be at least 300 sq ft');
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('http://localhost:5000/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.success) {
                priceSpan.textContent = data.formatted_price;
                rangeSpan.innerHTML = `${data.confidence_range.formatted_lower} - ${data.confidence_range.formatted_upper}`;
                resultDiv.style.display = 'block';
                priceSpan.classList.add('pulse');
                setTimeout(() => priceSpan.classList.remove('pulse'), 1000);
                resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

                // Refresh history if tab is active
                if (document.getElementById('history-tab').classList.contains('active')) {
                    loadHistory();
                    loadHistoryStats();
                }
            } else {
                showError(data.error || 'Prediction failed');
            }
        } catch (error) {
            showError('Cannot connect to server. Make sure Flask is running on port 5000');
            console.error(error);
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        if (isLoading) {
            predictBtn.innerHTML = '<span class="loading"></span> Predicting...';
            predictBtn.disabled = true;
        } else {
            predictBtn.innerHTML = 'Predict Price';
            predictBtn.disabled = false;
        }
    }

    function showError(message) {
        errorMessageSpan.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => { errorDiv.style.display = 'none'; }, 5000);
    }

    const inputs = document.querySelectorAll('input[type="number"]');
    inputs.forEach(input => {
        input.addEventListener('input', function () {
            const min = parseFloat(this.min);
            const max = parseFloat(this.max);
            let value = parseFloat(this.value);
            if (isNaN(value)) value = min;
            if (value < min) this.value = min;
            if (value > max) this.value = max;
        });
    });
});

// Feedback Modal
let currentFeedbackId = null;

function showFeedbackModal(predictionId) {
    currentFeedbackId = predictionId;
    document.getElementById('feedbackModal').style.display = 'flex';
}

function closeFeedbackModal() {
    document.getElementById('feedbackModal').style.display = 'none';
    currentFeedbackId = null;
    document.getElementById('actualPrice').value = '';
}

function submitFeedback() {
    const actualPrice = document.getElementById('actualPrice').value;
    const rating = document.querySelector('.star.active')?.getAttribute('data-rating') || 3;

    if (!actualPrice) {
        alert('Please enter the actual sale price');
        return;
    }

    fetch(`http://localhost:5000/api/feedback/${currentFeedbackId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            actual_price: parseFloat(actualPrice),
            user_rating: parseInt(rating)
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Thank you for your feedback! The model will be improved.');
                closeFeedbackModal();
                location.reload(); // Refresh to see updated history
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to submit feedback');
        });
}

// Star rating setup
document.addEventListener('click', function (e) {
    if (e.target.classList.contains('star')) {
        const rating = e.target.getAttribute('data-rating');
        document.querySelectorAll('.star').forEach(star => {
            if (star.getAttribute('data-rating') <= rating) {
                star.classList.add('active');
            } else {
                star.classList.remove('active');
            }
        });
    }
});