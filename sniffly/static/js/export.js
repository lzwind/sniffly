// Export functionality for Claude Analytics

const ExportModule = {
  // Export the dashboard to a ZIP file containing PDF report and chart images
  async exportDashboard() {
    try {
      this.showProgress('Preparing export...');
            
      // Step 1: Capture stat cards
      this.updateProgress(5, 'Capturing statistics...');
      const statsImage = await this.captureStatCards();
            
      // Step 2: Capture all charts
      this.updateProgress(10, 'Capturing charts...');
      const charts = await this.captureAllCharts();
            
      // Step 3: Generate PDF
      this.updateProgress(50, 'Generating PDF report...');
      const pdfArrayBuffer = await this.generatePDF(charts);
            
      // Step 4: Create ZIP
      this.updateProgress(80, 'Creating ZIP file...');
      const zip = new JSZip();
            
      // Add PDF to ZIP
      zip.file('analytics_report.pdf', pdfArrayBuffer);
            
      // Add stats image
      if (statsImage) {
        zip.file('overview_statistics.png', statsImage, {base64: true});
      }
            
      // Add charts folder
      const chartsFolder = zip.folder('charts');
      charts.forEach(chart => {
        chartsFolder.file(chart.name + '.png', chart.image, {base64: true});
      });
            
      // Generate ZIP
      this.updateProgress(90, 'Finalizing export...');
      const content = await zip.generateAsync({type: 'blob'});
            
      // Download ZIP with log directory name
      const date = new Date().toISOString().split('T')[0];
      const time = new Date().toISOString().split('T')[1].split(':').slice(0,2).join('-');
            
      // Get log directory name from current project
      let logDirName = 'sniffly';
      if (statistics.overview.log_dir_name) {
        logDirName = statistics.overview.log_dir_name;
      } else if (window.location.port === '8081') {
        // Try to get from project selector if in local mode
        const selector = document.getElementById('project-selector');
        if (selector && selector.value) {
          logDirName = selector.value;
        }
      }
            
      const filename = `${logDirName}_${date}_${time}.zip`;
      this.downloadFile(content, filename);
            
      this.updateProgress(100, 'Export complete!');
      setTimeout(() => this.hideProgress(), 1000);
            
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed: ' + error.message);
      this.hideProgress();
    }
  },

  // Capture all charts as base64 images
  async captureAllCharts() {
    const chartData = [];
    const SCALE = 2; // Or 3 for higher resolution
    const TITLE_PADDING = 40; // Space for title
    const chartConfigs = [
      { id: 'command-complexity-chart', name: 'command-complexity', title: 'Command Complexity Over Time' },
      { id: 'command-length-chart', name: 'command-length', title: 'Command Length Over Time' },
      { id: 'error-distribution-chart', name: 'error-distribution', title: 'Error Type Distribution' },
      { id: 'tool-trends-chart', name: 'tool-trends', title: 'Tool Usage Trends' },
      { id: 'daily-cost-chart', name: 'daily-cost', title: 'Daily Cost Breakdown' },
      { id: 'tokens-chart', name: 'token-usage', title: 'Token Usage' },
      { id: 'tools-chart', name: 'tool-usage', title: 'Tool Usage' },
      { id: 'user-interactions-chart', name: 'user-interactions', title: 'User Command Analysis' },
      { id: 'interruption-rate-trend-chart', name: 'interruption-rate-trend', title: 'Interruption Rate' },
      { id: 'error-rate-trend-chart', name: 'error-rate-trend', title: 'Error Rate Over Time' },
      { id: 'model-usage-chart', name: 'model-usage', title: 'Model Usage Distribution' },
      { id: 'hourly-tokens-chart', name: 'hourly-tokens', title: 'Token Usage by Hour' }
    ];
        
    for (const config of chartConfigs) {
      const canvas = document.getElementById(config.id);
      if (canvas && canvas.toDataURL) {
        const originalWidth = canvas.width;
        const originalHeight = canvas.height;
        const width = originalWidth * SCALE;
        const height = (originalHeight + TITLE_PADDING) * SCALE;

        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = width;
        tempCanvas.height = height;

        const tempCtx = tempCanvas.getContext('2d');

        // White background
        tempCtx.fillStyle = '#ffffff';
        tempCtx.fillRect(0, 0, width, height);

        // Scale everything
        tempCtx.scale(SCALE, SCALE);

        // Title
        tempCtx.fillStyle = '#333333';
        tempCtx.textAlign = 'center';
        tempCtx.font = 'bold 20px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        tempCtx.textBaseline = 'middle';
        tempCtx.fillText(config.title, originalWidth / 2, TITLE_PADDING / 2);

        // Chart
        tempCtx.drawImage(canvas, 0, TITLE_PADDING);

        // Export
        const imageData = tempCanvas.toDataURL('image/png');
        chartData.push({
          name: config.name,
          image: imageData.split(',')[1]
        });
      }
    }

        
    return chartData;
  },

  // Capture stat cards as a single image
  async captureStatCards() {
    try {
      const statsGrid = document.getElementById('overview-stats');
      if (!statsGrid) {return null;}
            
      // Hide all tooltips before capturing
      const tooltips = statsGrid.querySelectorAll('.tooltip-dark, .tooltip-info-icon + div, [id*="tooltip"]');
      const originalDisplay = [];
      tooltips.forEach((tooltip, index) => {
        originalDisplay[index] = tooltip.style.display;
        tooltip.style.display = 'none';
      });
            
      // Also hide tooltip icons temporarily
      const tooltipIcons = statsGrid.querySelectorAll('.tooltip-info-icon');
      const originalIconDisplay = [];
      tooltipIcons.forEach((icon, index) => {
        originalIconDisplay[index] = icon.style.display;
        icon.style.display = 'none';
      });
            
      let imageData = null;
            
      // Temporarily force optimal layout for export
      const statCards = statsGrid.querySelectorAll('.stat-card');
      const originalGridTemplate = statsGrid.style.gridTemplateColumns;
            
      // Force 3x2 layout for 6 cards, 2x2 for 4 cards, etc.
      if (statCards.length === 6) {
        statsGrid.style.gridTemplateColumns = 'repeat(3, 1fr)';
      } else if (statCards.length === 4) {
        statsGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
      }
            
      // Use html2canvas library if available, otherwise use DOM-to-canvas approach
      if (typeof html2canvas !== 'undefined') {
        const canvas = await html2canvas(statsGrid, {
          backgroundColor: '#ffffff',
          scale: 2, // Higher quality
          logging: false,
          useCORS: true,
          allowTaint: true
        });
        imageData = canvas.toDataURL('image/png').split(',')[1];
      } else {
        // Fallback: Manual canvas rendering
        imageData = this.renderStatsToCanvas();
      }
            
      // Restore original grid layout
      statsGrid.style.gridTemplateColumns = originalGridTemplate || '';
            
      // Restore tooltips
      tooltips.forEach((tooltip, index) => {
        tooltip.style.display = originalDisplay[index] || '';
      });
            
      // Restore tooltip icons
      tooltipIcons.forEach((icon, index) => {
        icon.style.display = originalIconDisplay[index] || '';
      });
            
      return imageData;
    } catch (error) {
      console.error('Failed to capture stat cards:', error);
      return null;
    }
  },

  // Manual rendering of stats to canvas (fallback)
  renderStatsToCanvas() {
    const statsGrid = document.getElementById('overview-stats');
    if (!statsGrid) {return null;}
        
    const statCards = statsGrid.querySelectorAll('.stat-card');
    if (statCards.length === 0) {return null;}
        
    // Create canvas
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
        
    // Calculate dimensions
    const cardWidth = 280;
    const cardHeight = 150;
    const padding = 20;
    const cols = 3;
    const rows = Math.ceil(statCards.length / cols);
        
    canvas.width = (cardWidth + padding) * cols + padding;
    canvas.height = (cardHeight + padding) * rows + padding;
        
    // White background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
        
    // Draw each stat card
    statCards.forEach((card, index) => {
      const col = index % cols;
      const row = Math.floor(index / cols);
      const x = padding + col * (cardWidth + padding);
      const y = padding + row * (cardHeight + padding);
            
      // Card background
      ctx.fillStyle = '#f8f9fa';
      ctx.strokeStyle = '#e0e0e0';
      ctx.lineWidth = 1;
      ctx.fillRect(x, y, cardWidth, cardHeight);
      ctx.strokeRect(x, y, cardWidth, cardHeight);
            
      // Extract text content
      const title = card.querySelector('h3')?.textContent.trim() || '';
      const value = card.querySelector('.value')?.textContent.trim() || '';
      const subtext = card.querySelector('.subtext')?.textContent.trim() || '';
      const breakdown = Array.from(card.querySelectorAll('.breakdown span'))
        .map(span => span.textContent.trim());
            
      // Draw title
      ctx.fillStyle = '#333333';
      ctx.font = 'bold 16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillText(title, x + 15, y + 25);
            
      // Draw value
      ctx.fillStyle = '#667eea';
      ctx.font = 'bold 32px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.fillText(value, x + 15, y + 65);
            
      // Draw subtext
      if (subtext) {
        ctx.fillStyle = '#666666';
        ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.fillText(subtext, x + 15, y + 85);
      }
            
      // Draw breakdown
      if (breakdown.length > 0) {
        ctx.fillStyle = '#888888';
        ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        breakdown.forEach((text, i) => {
          ctx.fillText(text, x + 15, y + 110 + (i * 15));
        });
      }
    });
        
    return canvas.toDataURL('image/png').split(',')[1];
  },

  // Generate PDF report
  async generatePDF(charts) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
        
    // Helper function to add wrapped text
    function addWrappedText(text, x, y, maxWidth, lineHeight) {
      const lines = doc.splitTextToSize(text, maxWidth);
      lines.forEach((line, i) => {
        doc.text(line, x, y + (i * lineHeight));
      });
      return y + (lines.length * lineHeight);
    }
        
    // Page 1: Title and Overview
    doc.setFontSize(24);
    doc.text('Claude Code Analytics Report', 105, 30, {align: 'center'});
        
    doc.setFontSize(14);
    const projectName = statistics.overview.project_name || 'Project Analysis';
    doc.text(projectName, 105, 45, {align: 'center'});
        
    doc.setFontSize(12);
    doc.text(new Date().toLocaleDateString(), 105, 55, {align: 'center'});
        
    // Summary Statistics
    doc.setFontSize(16);
    doc.text('Summary Statistics', 20, 80);
        
    doc.setFontSize(11);
    let y = 95;
    const lineHeight = 7;
        
    // Key metrics
    const metrics = [
      `Total Commands Analyzed: ${statistics.user_interactions?.user_commands_analyzed || 0}`,
      `Sessions: ${statistics.overview.sessions}`,
      `Duration: ${StatsModule.calculateDaysInclusive(statistics)} days`,
      `Total Messages: ${statistics.overview.total_messages.toLocaleString()}`,
      '',
      `User Interruption Rate: ${statistics.user_interactions?.interruption_rate || 0}%`,
      `Tool Usage Rate: ${statistics.user_interactions?.percentage_requiring_tools || 0}%`,
      `Average Steps per Command: ${statistics.user_interactions?.avg_steps_per_command || 0}`,
      `Average Tools per Command: ${statistics.user_interactions?.avg_tools_per_command || 0}`,
      '',
      `Total Tokens: ${formatNumber(statistics.overview.total_tokens.input + statistics.overview.total_tokens.output)}`,
      `  - Input: ${formatNumber(statistics.overview.total_tokens.input)}`,
      `  - Output: ${formatNumber(statistics.overview.total_tokens.output)}`,
      `  - Cache Created: ${formatNumber(statistics.overview.total_tokens.cache_creation)}`,
      `  - Cache Read: ${formatNumber(statistics.overview.total_tokens.cache_read)}`,
      `Cache Hit Rate: ${statistics.cache?.hit_rate || 0}%`,
      `Cache Efficiency: ${statistics.cache?.efficiency || 0}%`
    ];
        
    metrics.forEach(metric => {
      if (y > 270) {
        doc.addPage();
        y = 20;
      }
      if (metric) {
        doc.text(metric, 20, y);
      }
      y += lineHeight;
    });
        
    // Page 2: Tool Usage
    doc.addPage();
    doc.setFontSize(16);
    doc.text('Tool Usage Analysis', 20, 20);
        
    doc.setFontSize(11);
    y = 35;
        
    if (statistics.tools && statistics.tools.usage) {
      const toolUsage = Object.entries(statistics.tools.usage)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15); // Top 15 tools
            
      doc.text('Top Tools by Usage:', 20, y);
      y += lineHeight * 1.5;
            
      toolUsage.forEach(([tool, count]) => {
        if (y > 270) {
          doc.addPage();
          y = 20;
        }
        doc.text(`${tool}: ${count} calls`, 25, y);
        y += lineHeight;
      });
    }
        
    // Page 3: Charts Reference
    doc.addPage();
    doc.setFontSize(16);
    doc.text('Analytics Charts', 20, 20);
        
    doc.setFontSize(11);
    doc.text('The following charts are included in the charts/ folder:', 20, 35);
        
    y = 50;
    const chartDescriptions = [
      'command-complexity.png - Average complexity trends',
      'command-length.png - Command token length over time',
      'error-distribution.png - Error type breakdown',
      'tool-trends.png - Tool usage trends over time',
      'daily-cost.png - Daily cost breakdown',
      'token-usage.png - Token usage over project duration',
      'tool-usage.png - Tool usage distribution',
      'user-interactions.png - User command analysis over time',
      'interruption-rate-trend.png - Interruption rate over time',
      'error-rate-trend.png - Error rate over time',
      'model-usage.png - AI model usage distribution',
      'hourly-tokens.png - Token usage by hour of day'
    ];
        
    chartDescriptions.forEach(desc => {
      doc.text('• ' + desc, 25, y);
      y += lineHeight;
    });
        
    // Return as ArrayBuffer
    return doc.output('arraybuffer');
  },

  // Progress modal functions
  showProgress(message) {
    let modal = document.getElementById('export-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'export-modal';
      modal.style.cssText = `
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.5);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
            `;
      modal.innerHTML = `
                <div style="
                    background: white;
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
                    min-width: 300px;
                ">
                    <h3 style="margin: 0 0 1rem 0;">Exporting Dashboard</h3>
                    <p id="export-status" style="margin: 0 0 1rem 0;">${message}</p>
                    <div style="
                        width: 100%;
                        height: 6px;
                        background: #eee;
                        border-radius: 3px;
                        overflow: hidden;
                    ">
                        <div id="export-progress-bar" style="
                            width: 0%;
                            height: 100%;
                            background: #667eea;
                            border-radius: 3px;
                            transition: width 0.3s ease;
                        "></div>
                    </div>
                </div>
            `;
      document.body.appendChild(modal);
    }
    document.getElementById('export-status').textContent = message;
  },

  updateProgress(percent, message) {
    const progressBar = document.getElementById('export-progress-bar');
    const status = document.getElementById('export-status');
    if (progressBar) {progressBar.style.width = percent + '%';}
    if (status) {status.textContent = message;}
  },

  hideProgress() {
    const modal = document.getElementById('export-modal');
    if (modal) {
      modal.remove();
    }
  },

  // Download helper
  downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
    
  // Export all charts for sharing (public method)
  async exportAllCharts() {
    return await this.captureAllCharts();
  },

  // Extract chart configurations from Chart.js instances for interactive sharing
  getChartConfigurations() {
    const chartConfigs = [];
    
    // Chart instances are stored in the chartInstances object in charts.js
    // We need to check if it exists and has been initialized
    if (typeof chartInstances === 'undefined') {
      console.warn('Chart instances not found');
      return chartConfigs;
    }
    
    // Map chart instance names to their display names
    // Order matches project-analytics.html chart order
    const chartMap = {
      commandComplexity: { name: 'commandComplexityChart', id: 'command-complexity-chart' },
      commandLength: { name: 'commandLengthChart', id: 'command-length-chart' },
      errorDistribution: { name: 'errorDistributionChart', id: 'error-distribution-chart' },
      toolTrends: { name: 'toolTrendsChart', id: 'tool-trends-chart' },
      dailyCost: { name: 'dailyCostChart', id: 'daily-cost-chart' },
      tokens: { name: 'tokensChart', id: 'tokens-chart' },
      tools: { name: 'toolsChart', id: 'tools-chart' },
      userInteractions: { name: 'userInteractionsChart', id: 'user-interactions-chart' },
      interruptionRate: { name: 'interruptionRateTrendChart', id: 'interruption-rate-trend-chart' },
      errorRate: { name: 'errorRateTrendChart', id: 'error-rate-trend-chart' },
      modelUsage: { name: 'modelUsageChart', id: 'model-usage-chart' },
      hourlyTokens: { name: 'hourlyTokensChart', id: 'hourly-tokens-chart' }
    };
    
    // Extract configurations from each chart instance
    Object.entries(chartMap).forEach(([instanceName, info]) => {
      const chart = chartInstances[instanceName];
      if (chart && chart.config) {
        chartConfigs.push({
          name: info.name,
          id: info.id,
          type: chart.config.type,
          data: JSON.parse(JSON.stringify(chart.config.data)), // Deep clone
          options: JSON.parse(JSON.stringify(chart.config.options)) // Deep clone
        });
      }
    });
    
    return chartConfigs;
  }
};

// Make export function available globally
function exportDashboard() {
  ExportModule.exportDashboard();
}