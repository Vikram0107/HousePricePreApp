// Global variables // From varshil09
let charts = {};
let plotlyChart = null;

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

    // Add this inside your switchTab function
if (tabName === 'history') {
    setTimeout(() => {
        loadHistory();
    }, 100);
}

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
            loadBoxplot();
            loadCorrelationTable();
        }, 100);
    }

    if (tabName === 'insights') {
        loadInsights();
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

// Load price distribution histogram
async function loadPriceDistribution() {
    try {
        const response = await fetch('http://localhost:5000/api/price-distribution');
        const data = await response.json();

        const ctx = document.getElementById('priceHistogram').getContext('2d');

        const minPrice = Math.min(...data.prices);
        const maxPrice = Math.max(...data.prices);
        const binCount = 40;
        const binWidth = (maxPrice - minPrice) / binCount;

        const bins = Array(binCount).fill(0);
        data.prices.forEach(price => {
            const binIndex = Math.min(Math.floor((price - minPrice) / binWidth), binCount - 1);
            bins[binIndex]++;
        });

        const labels = Array(binCount).fill().map((_, i) => {
            const start = minPrice + i * binWidth;
            const end = start + binWidth;
            return `$${Math.round(start / 1000)}k-$${Math.round(end / 1000)}k`;
        });

        if (charts.priceHistogram) charts.priceHistogram.destroy();

        charts.priceHistogram = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Number of Houses',
                    data: bins,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'top' } },
                scales: {
                    y: { title: { display: true, text: 'Frequency' } },
                    x: { ticks: { rotation: 45, autoSkip: true, maxTicksLimit: 10 } }
                }
            }
        });
    } catch (error) {
        console.error('Error loading price distribution:', error);
    }
}

// Load boxplot
async function loadBoxplot() {
    try {
        const response = await fetch('http://localhost:5000/api/boxplot-data?feature=Neighborhood');
        const data = await response.json();

        const trace = {
            y: data.data,
            type: 'box',
            name: data.categories,
            boxpoints: 'all',
            jitter: 0.3,
            pointpos: -1.8,
            marker: { color: 'rgba(54, 162, 235, 0.5)' }
        };

        const layout = {
            title: 'Price Distribution by Neighborhood',
            xaxis: { title: 'Neighborhood', tickangle: -45 },
            yaxis: { title: 'Price ($)', tickformat: '$,.0f' },
            height: 500
        };

        Plotly.newPlot('boxplotChart', [trace], layout);
    } catch (error) {
        console.error('Error loading boxplot:', error);
    }
}

// Load insights
async function loadInsights() {
    try {
        const neighborhoodResponse = await fetch('http://localhost:5000/api/price-by-neighborhood');
        const neighborhoodData = await neighborhoodResponse.json();

        const topNeighborhoods = neighborhoodData.neighborhoods.slice(0, 5);
        const topPrices = neighborhoodData.means.slice(0, 5);

        const bestNeighborhoodsHtml = topNeighborhoods.map((hood, i) =>
            `<div class="insight-item">
                <strong>${hood}</strong>: $${topPrices[i].toLocaleString()}
                <span class="badge">Top ${i + 1}</span>
            </div>`
        ).join('');
        document.getElementById('best-neighborhoods').innerHTML = bestNeighborhoodsHtml;

        const importanceResponse = await fetch('http://localhost:5000/api/feature-importance');
        const importanceData = await importanceResponse.json();

        const topFeatures = importanceData.features.slice(0, 5);
        const topImportance = importanceData.importance.slice(0, 5);

        const valuableFeaturesHtml = topFeatures.map((feature, i) =>
            `<div class="insight-item">
                <strong>${feature.replace(/([A-Z])/g, ' $1').trim()}</strong>
                <span class="badge">Impact: ${(topImportance[i] / topImportance[0] * 100).toFixed(0)}%</span>
            </div>`
        ).join('');
        document.getElementById('valuable-features').innerHTML = valuableFeaturesHtml;

        const appreciationFactors = [
            "🏗️ <strong>Higher Overall Quality</strong> - Each point increase adds ~15-20% to value",
            "📐 <strong>Larger Living Area</strong> - Every 100 sq ft adds ~$15,000",
            "🚗 <strong>Garage Capacity</strong> - Each additional garage space adds ~$10,000",
            "🛏️ <strong>More Bathrooms</strong> - Full bathroom adds ~$20,000",
            "🔥 <strong>Fireplaces</strong> - Having a fireplace adds ~$15,000"
        ];
        document.getElementById('appreciation-factors').innerHTML = appreciationFactors.map(f => `<div class="insight-item">${f}</div>`).join('');

        const depreciationFactors = [
            "📅 <strong>Older Construction</strong> - Each decade older reduces value by ~5-8%",
            "🔧 <strong>Poor Condition</strong> - Below average condition reduces value by ~20%",
            "🏚️ <strong>Small Lot Size</strong> - Below median lot size reduces value by ~10%",
            "🅿️ <strong>No Garage</strong> - Reduces value by ~$15,000-20,000",
            "🌆 <strong>Undesirable Neighborhood</strong> - Can reduce value by 30-40%"
        ];
        document.getElementById('depreciation-factors').innerHTML = depreciationFactors.map(f => `<div class="insight-item">${f}</div>`).join('');

        const recommendations = `
            <p>🎯 <strong>Best Investment Strategy:</strong></p>
            <ul>
                <li>Focus on neighborhoods: ${topNeighborhoods.slice(0, 3).join(', ')}</li>
                <li>Prioritize houses with Overall Quality ≥ 7</li>
                <li>Look for properties with garage capacity ≥ 2 cars</li>
                <li>Consider houses built after 2000 for better appreciation</li>
                <li>Aim for living area between 1,500-2,500 sq ft for best ROI</li>
            </ul>
            <p>💰 <strong>Expected ROI:</strong> Properties in top neighborhoods with high quality ratings typically appreciate 5-8% annually.</p>
        `;
        document.getElementById('recommendations').innerHTML = recommendations;
    } catch (error) {
        console.error('Error loading insights:', error);
    }
}

// Prediction form handling
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('predictionForm');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    const priceSpan = document.getElementById('price');
    const rangeSpan = document.getElementById('range');
    const errorMessageSpan = document.getElementById('errorMessage');
    const predictBtn = document.querySelector('.predict-btn');

    form.addEventListener('submit', async function(e) {
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
        input.addEventListener('input', function() {
            const min = parseFloat(this.min);
            const max = parseFloat(this.max);
            let value = parseFloat(this.value);
            if (isNaN(value)) value = min;
            if (value < min) this.value = min;
            if (value > max) this.value = max;
        });
    });
});

// Load prediction history
async function loadHistory() {
    try {
        const response = await fetch('http://localhost:5000/api/history');
        const data = await response.json();

        if (data.success) {
            displayHistory(data.history);
            loadHistoryStats();
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
                loadHistory(); // Refresh the history
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
                loadHistory(); // Refresh the history
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
    // Create toast element if it doesn't exist
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
