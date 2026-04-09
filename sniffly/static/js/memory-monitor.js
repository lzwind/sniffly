// Memory monitoring utility for Claude Analytics

const MemoryMonitor = {
  // Track memory usage of different components
  measurements: {
    initial: null,
    afterStats: null,
    afterMessages: null,
    afterCharts: null,
    current: null
  },
    
  // Get current memory usage if available
  getMemoryInfo() {
    if ('memory' in performance) {
      return {
        used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
        total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
        limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
      };
    }
    return null;
  },
    
  // Take a memory snapshot with label
  snapshot(label) {
    const memory = this.getMemoryInfo();
    if (memory) {
      this.measurements[label] = memory;
    }
    return memory;
  },
    
  // Calculate size of a JavaScript object
  estimateSize(obj) {
    if (!obj) {return 0;}
        
    try {
      // Convert to JSON to estimate size
      const jsonStr = JSON.stringify(obj);
      const sizeBytes = new Blob([jsonStr]).size;
      return Math.round(sizeBytes / 1024 / 1024 * 100) / 100; // MB with 2 decimals
    } catch (e) {
      console.error('Failed to estimate size:', e);
      return 0;
    }
  },
    
  // Get detailed breakdown of memory usage
  getMemoryBreakdown() {
    const breakdown = {
      timestamp: new Date().toISOString(),
      heap: this.getMemoryInfo(),
      components: {}
    };
        
    // Estimate size of major data structures
    if (typeof window !== 'undefined') {
      // Global data
      if (window.statistics) {
        breakdown.components.statistics = this.estimateSize(window.statistics);
      }
            
      if (window.allMessages) {
        breakdown.components.messages = {
          count: window.allMessages.length,
          size: this.estimateSize(window.allMessages),
          loaded: window.messagesFullyLoaded ? 'all' : 'partial'
        };
      }
            
      if (window.filteredMessages) {
        breakdown.components.filteredMessages = {
          count: window.filteredMessages.length,
          size: this.estimateSize(window.filteredMessages)
        };
      }
            
      // Chart data
      if (window.chartInstances) {
        breakdown.components.charts = {
          count: Object.keys(window.chartInstances).length,
          instances: Object.keys(window.chartInstances)
        };
      }
            
      // Command details
      if (window.originalCommandDetails) {
        breakdown.components.commandDetails = {
          count: window.originalCommandDetails.length,
          size: this.estimateSize(window.originalCommandDetails)
        };
      }
            
      // JSONL data if loaded
      if (window.currentJsonlData) {
        breakdown.components.jsonlData = {
          lines: window.currentJsonlData.length,
          size: this.estimateSize(window.currentJsonlData)
        };
      }
    }
        
    return breakdown;
  },
    
  // Print memory report to console
  printReport() {
    const breakdown = this.getMemoryBreakdown();
        
    console.group('📊 Memory Usage Report');
        
    // Heap usage
    if (breakdown.heap) {
      console.log(`Heap: ${breakdown.heap.used}MB / ${breakdown.heap.total}MB (Limit: ${breakdown.heap.limit}MB)`);
      const usage = (breakdown.heap.used / breakdown.heap.limit * 100).toFixed(1);
      console.log(`Usage: ${usage}% of limit`);
    } else {
      console.log('⚠️  Memory API not available (use Chrome with --enable-precise-memory-info)');
    }
        
    // Component breakdown
    console.group('Component Sizes:');
    let totalSize = 0;
        
    for (const [component, data] of Object.entries(breakdown.components)) {
      if (typeof data === 'object' && data.size !== undefined) {
        console.log(`${component}: ${data.size}MB ${data.count ? `(${data.count} items)` : ''}`);
        totalSize += data.size;
      } else if (typeof data === 'number') {
        console.log(`${component}: ${data}MB`);
        totalSize += data;
      } else {
        console.log(`${component}:`, data);
      }
    }
        
    console.log('─────────────────');
    console.log(`Total tracked: ${totalSize.toFixed(2)}MB`);
    console.groupEnd();
        
    // Memory growth
    if (this.measurements.initial && breakdown.heap) {
      const growth = breakdown.heap.used - this.measurements.initial.used;
      console.log(`Memory growth since load: ${growth >= 0 ? '+' : ''}${growth}MB`);
    }
        
    console.groupEnd();
        
    return breakdown;
  },
    
  // Monitor memory growth over time
  startMonitoring(intervalMs = 10000) {
    if (this.monitorInterval) {
      this.stopMonitoring();
    }
        
    console.log(`🔍 Starting memory monitoring (every ${intervalMs/1000}s)`);
    this.monitorInterval = setInterval(() => {
      const memory = this.getMemoryInfo();
      if (memory) {
        console.log(`[Memory] ${new Date().toLocaleTimeString()}: ${memory.used}MB / ${memory.total}MB`);
      }
    }, intervalMs);
  },
    
  stopMonitoring() {
    if (this.monitorInterval) {
      clearInterval(this.monitorInterval);
      this.monitorInterval = null;
      console.log('🛑 Stopped memory monitoring');
    }
  },
    
  // Analyze message memory usage
  analyzeMessages() {
    if (!window.allMessages) {
      console.log('No messages loaded');
      return;
    }
        
    const analysis = {
      totalMessages: window.allMessages.length,
      totalSize: this.estimateSize(window.allMessages),
      avgSizePerMessage: 0,
      largestMessages: []
    };
        
    // Find largest messages
    const messageSizes = window.allMessages.map((msg, index) => ({
      index,
      size: this.estimateSize(msg),
      type: msg.type,
      contentLength: msg.content?.length || 0
    })).sort((a, b) => b.size - a.size);
        
    analysis.avgSizePerMessage = (analysis.totalSize / analysis.totalMessages * 1024).toFixed(2); // KB
    analysis.largestMessages = messageSizes.slice(0, 5);
        
    console.group('📨 Message Memory Analysis');
    console.log(`Total: ${analysis.totalMessages} messages using ${analysis.totalSize}MB`);
    console.log(`Average: ${analysis.avgSizePerMessage}KB per message`);
    console.log('Largest messages:');
    console.table(analysis.largestMessages);
    console.groupEnd();
        
    return analysis;
  }
};

// Add console commands
if (typeof window !== 'undefined') {
  window.MemoryMonitor = MemoryMonitor;
    
  // Add convenient console commands
  window.memoryReport = () => MemoryMonitor.printReport();
  window.memoryAnalyze = () => MemoryMonitor.analyzeMessages();
  window.memoryStart = (interval) => MemoryMonitor.startMonitoring(interval);
  window.memoryStop = () => MemoryMonitor.stopMonitoring();
    
  // Only show console message if memory monitor is enabled
  // Check after DOM is loaded to ensure config is available
  const showMemoryMonitorMessage = () => {
    if (window.memoryMonitorEnabled) {
      console.log(`💾 Memory Monitor loaded. Available commands:
    • memoryReport() - Show current memory usage breakdown
    • memoryAnalyze() - Analyze message memory usage
    • memoryStart(ms) - Start monitoring (default: 10s)
    • memoryStop() - Stop monitoring
    
    Note: For accurate heap measurements, run Chrome with:
    --enable-precise-memory-info`);
    }
  };
    
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showMemoryMonitorMessage);
  } else {
    // DOM already loaded, check immediately
    showMemoryMonitorMessage();
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MemoryMonitor;
}