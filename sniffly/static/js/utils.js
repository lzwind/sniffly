// Utility functions for Claude Analytics

// Format large numbers with K/M suffixes
function formatNumber(num) {
  if (num === 0) {return '0';}
  if (num < 1000) {return num.toString();}
  if (num < 1000000) {return (num / 1000).toFixed(1) + 'K';}
  return (num / 1000000).toFixed(1) + 'M';
}

// Format token counts as input/output
function formatTokens(tokens) {
  // User messages don't have token counts
  if (tokens.input === 0 && tokens.output === 0) {
    return '-';
  }
  const input = formatNumber(tokens.input);
  const output = formatNumber(tokens.output);
  return `${input}/${output}`;
}

// Format timestamp with full date and time
function formatTimestamp(timestamp) {
  if (!timestamp) {return 'N/A';}
  const date = new Date(timestamp);
    
  // Show full date and time in local timezone
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  });
}

// Format model name
function formatModelName(model) {
  return model || '-';
}

// Format date to short format
function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Truncate content for table display
function truncateContent(content) {
  const maxLength = 200;
  const maxLineLength = 80;
    
  // First, check if any line is too long (handles the box-drawing character case)
  const lines = content.split('\n');
  let truncated = false;
    
  const processedLines = lines.map(line => {
    // Check for very long unbroken strings
    if (line.length > maxLineLength && !line.includes(' ')) {
      truncated = true;
      return line.substring(0, maxLineLength) + '...';
    }
    return line;
  });
    
  let result = processedLines.join('\n');
    
  // Then apply overall length limit
  if (result.length > maxLength) {
    result = result.substring(0, maxLength) + '...';
    truncated = true;
  }
    
  return result;
}

// Debounce function for rate limiting
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Check if a message is an interruption
function isInterruptionMessage(content) {
  return USER_INTERRUPTION_PATTERNS.some(pattern => content.startsWith(pattern));
}

// Tooltip utility functions
function showTooltip(tooltipId) {
  const tooltip = document.getElementById(tooltipId);
  if (tooltip) {
    tooltip.style.display = 'block';
  }
}

function hideTooltip(tooltipId) {
  const tooltip = document.getElementById(tooltipId);
  if (tooltip) {
    tooltip.style.display = 'none';
  }
}

// Initialize standard hover tooltips
function initHoverTooltip(triggerId, tooltipId) {
  const trigger = document.getElementById(triggerId);
  const tooltip = document.getElementById(tooltipId);
    
  if (!trigger || !tooltip) {return;}
    
  trigger.addEventListener('mouseenter', () => showTooltip(tooltipId));
  trigger.addEventListener('mouseleave', () => hideTooltip(tooltipId));
}

// Create dynamic tooltip with both click and hover
function createDynamicTooltip(targetElement, content, options = {}) {
  // Remove any existing tooltip
  const existingTooltip = targetElement.querySelector('.tooltip-dark');
  if (existingTooltip) {
    existingTooltip.remove();
  }
    
  // Create tooltip element
  const tooltip = document.createElement('div');
  tooltip.className = 'tooltip-dark';
  tooltip.style.position = 'absolute';
  tooltip.innerHTML = content;
    
  // Set positioning
  const position = options.position || 'top-right';
  switch(position) {
  case 'top-right':
    tooltip.style.top = '20px';
    tooltip.style.right = '0';
    break;
  case 'top-left':
    tooltip.style.top = '20px';
    tooltip.style.left = '-10px';
    break;
  default:
    tooltip.style.top = '20px';
    tooltip.style.left = '0';
  }
    
  // Set width if specified
  if (options.width) {
    tooltip.style.width = options.width;
  }
    
  targetElement.style.position = 'relative';
  targetElement.appendChild(tooltip);
    
  // Event handlers
  let hideTimeout;
  const showFn = () => {
    clearTimeout(hideTimeout);
    tooltip.style.display = 'block';
  };
    
  const hideFn = () => {
    hideTimeout = setTimeout(() => {
      tooltip.style.display = 'none';
    }, options.delay || 100);
  };
    
  // Add both click and hover listeners
  targetElement.addEventListener('click', showFn);
  targetElement.addEventListener('mouseenter', showFn);
  targetElement.addEventListener('mouseleave', hideFn);
    
  return tooltip;
}

// Copy text to clipboard with UI feedback
function copyToClipboard(text, event) {
  if (event) {
    event.stopPropagation();
  }
  navigator.clipboard.writeText(text).then(() => {
    // Show brief feedback
    const original = event ? event.target.textContent : '';
    if (event && event.target) {
      event.target.textContent = 'Copied!';
      setTimeout(() => {
        event.target.textContent = original;
      }, 1000);
    }
  });
}

// Get content preview for JSONL line
function getJsonlContentPreview(line) {
  if (line.type === 'summary') {
    return line.summary || 'Summary';
  }
    
  if (line.message && line.message.content) {
    const content = line.message.content;
    if (Array.isArray(content) && content.length > 0) {
      const firstItem = content[0];
      if (firstItem.type === 'text') {
        return firstItem.text || '';
      } else if (firstItem.type === 'tool_use') {
        return `Tool: ${firstItem.name}`;
      } else if (firstItem.type === 'tool_result') {
        const preview = firstItem.content || '';
        // Handle different types of content
        if (typeof preview === 'string') {
          return preview.substring(0, 100) + (preview.length > 100 ? '...' : '');
        } else if (typeof preview === 'boolean') {
          return String(preview);
        } else if (typeof preview === 'object') {
          return JSON.stringify(preview).substring(0, 100) + '...';
        } else {
          return String(preview);
        }
      }
    } else if (typeof content === 'string') {
      return content;
    }
  }
    
  return 'No content';
}

// Format date range for display (refactored to accept parameters)
function formatDateRange(startDate, endDate) {
  const start = new Date(startDate);
  const end = new Date(endDate);
  return `${start.toLocaleDateString()} - ${end.toLocaleDateString()}`;
}

// Export for use in other scripts
// Highlight a table row temporarily
// This function only manipulates the passed DOM element, no document access needed
function highlightRow(row, duration = 1500) {
  if (row) {
    row.style.backgroundColor = '#ffffcc';
    setTimeout(() => {
      row.style.backgroundColor = '';
    }, duration);
  }
}

// Format file size in human-readable format
function formatFileSize(bytes) {
  if (bytes === 0) {return '0 Bytes';}
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Format duration in human-readable format
function formatDuration(seconds) {
  if (seconds < 60) {return `${seconds}s`;}
  if (seconds < 3600) {return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;}
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

// Generic table sorting function
function sortTableData(data, sortColumn, sortDirection, columnConfig) {
  data.sort((a, b) => {
    let aVal, bVal;
        
    // If custom value extractor provided for this column, use it
    if (columnConfig && columnConfig[sortColumn]) {
      const extractor = columnConfig[sortColumn];
      aVal = extractor(a);
      bVal = extractor(b);
    } else {
      // Default: just get the property value
      aVal = a[sortColumn] || '';
      bVal = b[sortColumn] || '';
    }
        
    // Compare values
    if (aVal < bVal) {return sortDirection === 'asc' ? -1 : 1;}
    if (aVal > bVal) {return sortDirection === 'asc' ? 1 : -1;}
    return 0;
  });
    
  return data;
}

// Navigate to a specific row in a paginated table
function goToRowInPaginatedTable(config) {
  const { inputId, dataArray, itemsPerPage, navigateFunction, tbodySelector } = config;
    
  const input = document.getElementById(inputId);
  const rowNum = parseInt(input.value);
  if (!rowNum || rowNum < 1) {return;}
    
  const index = rowNum - 1;
  if (index >= dataArray.length) {
    alert(`Row ${rowNum} does not exist. Total rows: ${dataArray.length}`);
    return;
  }
    
  // Calculate which page this row is on
  const page = Math.floor(index / itemsPerPage) + 1;
    
  // Go to that page
  navigateFunction(page);
    
  // Highlight the row briefly
  setTimeout(() => {
    const rows = document.querySelectorAll(`${tbodySelector} tr`);
    const rowIndex = index % itemsPerPage;
    highlightRow(rows[rowIndex]);
  }, 100);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    copyToClipboard,
    createDynamicTooltip,
    debounce,
    escapeHtml,
    formatDate,
    formatDateRange,
    formatDuration,
    formatFileSize,
    formatNumber,
    formatTokens,
    formatTimestamp,
    formatModelName,
    isInterruptionMessage,
    showTooltip,
    hideTooltip,
    highlightRow,
    initHoverTooltip,
    getJsonlContentPreview,
    truncateContent,
    sortTableData,
    goToRowInPaginatedTable,
    exportToCSV,
    downloadCSV,
    downloadMarkdown
  };
}

// Export data to CSV format
function exportToCSV(data, headers) {
  // Create CSV header row
  const csvHeaders = headers.map(h => `"${h}"`).join(',');
    
  // Create CSV data rows
  const csvRows = data.map(row => {
    return row.map(cell => {
      // Escape quotes and wrap in quotes
      const cellStr = String(cell || '').replace(/"/g, '""');
      return `"${cellStr}"`;
    }).join(',');
  });
    
  // Combine header and rows
  return [csvHeaders, ...csvRows].join('\n');
}

// Download CSV file
function downloadCSV(csvContent, filename) {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');

  if (navigator.msSaveBlob) { // IE 10+
    navigator.msSaveBlob(blob, filename);
  } else {
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

// Download Markdown file
function downloadMarkdown(content, filename) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}