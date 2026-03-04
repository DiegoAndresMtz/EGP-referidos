
    (function () {
        const canvas = document.getElementById('advisorsChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        const advisors = [
            
        "Name Last",
        
    ];

    const ganados = [
        
    { { advisor_performance.get(adv.id, {}).get('ganados', 0) } },
    
    ];

    const enProceso = [
        
    { { advisor_performance.get(adv.id, {}).get('en_proceso', 0) } },
    
    ];

    const perdidos = [
        
    { { advisor_performance.get(adv.id, {}).get('perdidos', 0) } },
    
    ];

    // Update summary totals
    const sumArr = arr => arr.reduce((a, b) => a + b, 0);
    document.getElementById('totalGanados').textContent = sumArr(ganados);
    document.getElementById('totalEnProceso').textContent = sumArr(enProceso);
    document.getElementById('totalPerdidos').textContent = sumArr(perdidos);

    // Gradient helpers
    function makeGradient(ctx, c1, c2) {
        const g = ctx.createLinearGradient(0, 0, 0, 400);
        g.addColorStop(0, c1);
        g.addColorStop(1, c2);
        return g;
    }

    const gradGanados = makeGradient(ctx, 'rgba(16, 185, 129, 0.9)', 'rgba(16, 185, 129, 0.35)');
    const gradEnProc = makeGradient(ctx, 'rgba(245, 158, 11, 0.9)', 'rgba(245, 158, 11, 0.35)');
    const gradPerdidos = makeGradient(ctx, 'rgba(239, 68, 68, 0.9)', 'rgba(239, 68, 68, 0.35)');

    const textPrimary = getComputedStyle(document.body).getPropertyValue('--text-primary').trim() || '#e2e8f0';
    const textSecondary = getComputedStyle(document.body).getPropertyValue('--text-secondary').trim() || '#94a3b8';

    // Shared tooltip config
    const tooltipConfig = {
        enabled: true,
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(15, 23, 42, 0.92)',
        titleColor: '#f1f5f9',
        bodyColor: '#cbd5e1',
        titleFont: { size: 13, weight: '700', family: 'Inter' },
        bodyFont: { size: 12, family: 'Inter' },
        padding: { top: 12, bottom: 12, left: 14, right: 14 },
        cornerRadius: 12,
        borderColor: 'rgba(139, 92, 246, 0.25)',
        borderWidth: 1,
        boxPadding: 6,
        usePointStyle: true,
        pointStyle: 'circle',
        callbacks: {
            label: function (context) {
                return '  ' + context.dataset.label + ': ' + context.parsed.y + ' leads';
            }
        }
    };

    // Chart config factory
    function getConfig(type) {
        if (type === 'doughnut') {
            const total = sumArr(ganados) + sumArr(enProceso) + sumArr(perdidos);
            return {
                type: 'doughnut',
                data: {
                    labels: ['Ganados', 'En Proceso', 'Perdidos'],
                    datasets: [{
                        data: [sumArr(ganados), sumArr(enProceso), sumArr(perdidos)],
                        backgroundColor: ['rgba(16,185,129,0.85)', 'rgba(245,158,11,0.85)', 'rgba(239,68,68,0.85)'],
                        borderColor: ['rgba(16,185,129,1)', 'rgba(245,158,11,1)', 'rgba(239,68,68,1)'],
                        borderWidth: 2,
                        hoverOffset: 12,
                        spacing: 4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    animation: { animateRotate: true, duration: 1200, easing: 'easeOutQuart' },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: textPrimary,
                                padding: 20,
                                font: { size: 12, weight: '600', family: 'Inter' },
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.92)',
                            titleColor: '#f1f5f9',
                            bodyColor: '#cbd5e1',
                            titleFont: { size: 13, weight: '700', family: 'Inter' },
                            bodyFont: { size: 12, family: 'Inter' },
                            padding: 14,
                            cornerRadius: 12,
                            borderColor: 'rgba(139, 92, 246, 0.25)',
                            borderWidth: 1,
                            callbacks: {
                                label: function (c) {
                                    const pct = total > 0 ? ((c.raw / total) * 100).toFixed(1) : 0;
                                    return '  ' + c.label + ': ' + c.raw + ' (' + pct + '%)';
                                }
                            }
                        }
                    }
                }
            };
        }

        if (type === 'line') {
            return {
                type: 'line',
                data: {
                    labels: advisors,
                    datasets: [
                        {
                            label: 'Ganados',
                            data: ganados,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 3,
                            pointBackgroundColor: '#10b981',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 6,
                            pointHoverRadius: 9,
                            fill: true,
                            tension: 0.4,
                        },
                        {
                            label: 'En Proceso',
                            data: enProceso,
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            borderWidth: 3,
                            pointBackgroundColor: '#f59e0b',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 6,
                            pointHoverRadius: 9,
                            fill: true,
                            tension: 0.4,
                        },
                        {
                            label: 'Perdidos',
                            data: perdidos,
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            borderWidth: 3,
                            pointBackgroundColor: '#ef4444',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 6,
                            pointHoverRadius: 9,
                            fill: true,
                            tension: 0.4,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 1200, easing: 'easeOutQuart' },
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: textPrimary,
                                padding: 20,
                                font: { size: 12, weight: '600', family: 'Inter' },
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        },
                        tooltip: tooltipConfig
                    },
                    scales: {
                        x: {
                            ticks: { color: textSecondary, font: { size: 11, weight: '500', family: 'Inter' } },
                            grid: { color: 'rgba(255, 255, 255, 0.04)', drawBorder: false }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: { stepSize: 1, color: textSecondary, font: { size: 11, family: 'Inter' } },
                            grid: { color: 'rgba(255, 255, 255, 0.06)', drawBorder: false }
                        }
                    }
                }
            };
        }

        // Default: bar
        return {
            type: 'bar',
            data: {
                labels: advisors,
                datasets: [
                    {
                        label: 'Ganados',
                        data: ganados,
                        backgroundColor: gradGanados,
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 0,
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                    {
                        label: 'En Proceso',
                        data: enProceso,
                        backgroundColor: gradEnProc,
                        borderColor: 'rgba(245, 158, 11, 1)',
                        borderWidth: 0,
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                    {
                        label: 'Perdidos',
                        data: perdidos,
                        backgroundColor: gradPerdidos,
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderWidth: 0,
                        borderRadius: 6,
                        borderSkipped: false,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 1200, easing: 'easeOutQuart' },
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: textPrimary,
                            padding: 20,
                            font: { size: 12, weight: '600', family: 'Inter' },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: tooltipConfig
                },
                scales: {
                    x: {
                        stacked: true,
                        ticks: { color: textSecondary, font: { size: 11, weight: '500', family: 'Inter' } },
                        grid: { display: false }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: { stepSize: 1, color: textSecondary, font: { size: 11, family: 'Inter' } },
                        grid: { color: 'rgba(255, 255, 255, 0.06)', drawBorder: false }
                    }
                }
            }
        };
    }

    // Create initial chart
    let currentChart = new Chart(canvas, getConfig('bar'));

    // Toggle buttons logic
    window.switchChart = function (type) {
        const btns = document.querySelectorAll('.chart-toggle-btn');
        btns.forEach(b => {
            if (b.dataset.type === type) {
                b.style.background = 'linear-gradient(135deg, #8b5cf6, #6366f1)';
                b.style.color = '#fff';
                b.style.boxShadow = '0 2px 8px rgba(139, 92, 246, 0.3)';
            } else {
                b.style.background = 'transparent';
                b.style.color = getComputedStyle(document.body).getPropertyValue('--text-muted') || '#94a3b8';
                b.style.boxShadow = 'none';
            }
        });
        currentChart.destroy();
        currentChart = new Chart(canvas, getConfig(type));
    };
}) ();
