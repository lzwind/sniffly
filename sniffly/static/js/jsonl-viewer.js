// JSONL Viewer Module for Claude Analytics

const JsonlViewer = (function() {
  // Private state
  let currentJsonlData = [];
  let filteredJsonlData = [];
  let jsonlSortColumn = 'line';
  let jsonlSortDirection = 'asc';
  let jsonlPage = 1;
  let jsonlPerPage = 50;
    
  // Private functions
  async function loadJsonlFileList() {
    try {
      // Get current project info
      const projectResponse = await fetch('/api/project');
      const projectData = await projectResponse.json();
            
      if (!projectData.log_dir_name) {
        console.error('No project selected');
        return;
      }
            
      const response = await fetch(`/api/jsonl-files?project=${projectData.log_dir_name}`);
      const files = await response.json();
            
      const select = document.getElementById('jsonlFileSelect');
      select.innerHTML = '<option value="">-- Select a file --</option>';
            
      if (files && files.length > 0) {
        let latestFile = null;
        let latestTimestamp = 0;
                
        // Add files to dropdown
        files.forEach(file => {
          const option = document.createElement('option');
          option.value = file.name;
                    
          // Format the display name with date and size
          const date = new Date(file.modified * 1000); // Convert Unix timestamp to milliseconds
          const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
          const sizeStr = formatFileSize(file.size);
          option.textContent = `${file.name} (${dateStr}, ${sizeStr})`;
                    
          select.appendChild(option);
                    
          // Track the latest file
          const fileTimestamp = file.modified || file.created || 0;
          if (fileTimestamp > latestTimestamp) {
            latestTimestamp = fileTimestamp;
            latestFile = file.name;
          }
        });
                
        // Auto-select the latest file
        if (latestFile && files.length > 0) {
          select.value = latestFile;
          // Automatically load the latest file
          loadJsonlFile(latestFile);
        }
      } else {
        showJsonlError('No JSONL files found for this project');
      }
    } catch (error) {
      console.error('Error loading JSONL files:', error);
      showJsonlError('Failed to load JSONL files: ' + error.message);
    }
  }
    
  async function loadJsonlFile(filename) {
    if (!filename) {return;}
        
    // Show loading state
    document.getElementById('jsonlLoading').style.display = 'block';
    document.getElementById('jsonlError').style.display = 'none';
    document.getElementById('jsonlTableContainer').style.display = 'none';
    document.getElementById('jsonlMetadata').style.display = 'none';
        
    try {
      // Get current project info
      const projectResponse = await fetch('/api/project');
      const projectData = await projectResponse.json();
            
      if (!projectData.log_dir_name) {
        showJsonlError('No project selected');
        return;
      }
            
      const response = await fetch(`/api/jsonl-content?file=${encodeURIComponent(filename)}&project=${projectData.log_dir_name}`);
      const data = await response.json();
            
      if (data.error) {
        showJsonlError(data.error);
        return;
      }
            
      // Store the data with original indices
      currentJsonlData = data.lines.map((line, index) => ({
        ...line,
        originalIndex: index
      }));
      filteredJsonlData = [...currentJsonlData];
            
      // Update stats
      document.getElementById('jsonlStats').textContent = 
                `Total: ${data.total_lines} lines | User: ${data.user_count} | Assistant: ${data.assistant_count}`;
            
      // Display metadata
      if (data.metadata) {
        displayJsonlMetadata(data.metadata, filename);
      }
            
      // Reset filters
      document.getElementById('jsonlTypeFilter').value = '';
      document.getElementById('jsonlSearchInput').value = '';
            
      // Show table and populate
      document.getElementById('jsonlTableContainer').style.display = 'block';
      populateJsonlTable(filteredJsonlData);
            
      // Update counts
      document.getElementById('jsonlTotalCount').textContent = currentJsonlData.length;
      document.getElementById('jsonlFilteredCount').textContent = filteredJsonlData.length;
            
    } catch (error) {
      console.error('Error loading JSONL file:', error);
      showJsonlError('Failed to load file: ' + error.message);
    } finally {
      document.getElementById('jsonlLoading').style.display = 'none';
    }
  }
    
  function populateJsonlTable(data) {
    const tbody = document.getElementById('jsonlTableBody');
    tbody.innerHTML = '';
        
    // Calculate pagination
    const start = (jsonlPage - 1) * jsonlPerPage;
    const end = start + jsonlPerPage;
    const pageData = data.slice(start, end);
        
    pageData.forEach((line, index) => {
      const row = tbody.insertRow();
      row.onclick = () => showJsonlDetails(line.originalIndex);
            
      // Line number
      const lineCell = row.insertCell();
      lineCell.className = 'line-number';
      lineCell.textContent = line.originalIndex + 1;
            
      // Type
      const typeCell = row.insertCell();
      const typeBadge = document.createElement('span');
      typeBadge.className = `type-badge type-${line.type || 'unknown'}`;
      typeBadge.textContent = line.type || 'unknown';
      typeCell.appendChild(typeBadge);
            
      // Timestamp
      const timestampCell = row.insertCell();
      timestampCell.style.fontSize = '0.85rem';
      timestampCell.style.color = '#666';
      if (line.timestamp) {
        const date = new Date(line.timestamp);
        timestampCell.textContent = date.toLocaleString();
      } else {
        timestampCell.textContent = '-';
      }
            
      // Content preview
      const contentCell = row.insertCell();
      contentCell.className = 'content-preview';
      contentCell.textContent = getJsonlContentPreview(line);
            
      // UUID
      const uuidCell = row.insertCell();
      uuidCell.style.fontSize = '0.75rem';
      uuidCell.style.color = '#999';
      uuidCell.style.fontFamily = 'monospace';
      uuidCell.textContent = line.uuid ? line.uuid.substring(0, 8) : '-';
    });
        
    // Update pagination display
    updatePaginationDisplay();
  }
    
  function updatePaginationDisplay() {
    const totalPages = Math.ceil(filteredJsonlData.length / jsonlPerPage);
    const paginationElement = document.getElementById('jsonl-pagination');
        
    // Show/hide pagination
    if (filteredJsonlData.length > jsonlPerPage) {
      paginationElement.style.display = 'flex';
    } else {
      paginationElement.style.display = 'none';
    }
        
    // Update page numbers
    document.getElementById('jsonl-total-pages').textContent = totalPages;
    document.getElementById('jsonl-page-input').value = jsonlPage;
        
    // Update button states
    document.getElementById('jsonl-prev-btn').disabled = jsonlPage === 1;
    document.getElementById('jsonl-next-btn').disabled = jsonlPage === totalPages;
  }
    
  function showJsonlDetails(index) {
    const line = currentJsonlData[index];
    if (!line) {return;}
        
    const modal = document.getElementById('message-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
        
    modalTitle.textContent = `JSONL Entry - Line ${index + 1}`;
    
    // Hide navigation for JSONL viewer
    const modalNav = document.querySelector('.modal-navigation');
    if (modalNav) {
      modalNav.style.display = 'none';
    }
        
    // Pretty print the JSON
    const jsonStr = JSON.stringify(line, null, 2);
    modalBody.innerHTML = `
            <pre style="background: #f5f5f5; padding: 1rem; border-radius: 4px; overflow: auto; max-height: 70vh;">
${escapeHtml(jsonStr)}
            </pre>
        `;
        
    modal.style.display = 'block';
  }
    
  function sortJsonlTable(column) {
    // Toggle sort direction if clicking the same column
    if (jsonlSortColumn === column) {
      jsonlSortDirection = jsonlSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      jsonlSortColumn = column;
      jsonlSortDirection = 'asc';
    }
        
    // Sort the filtered data
    filteredJsonlData.sort((a, b) => {
      let aVal = a[column] || '';
      let bVal = b[column] || '';
            
      if (column === 'line') {
        aVal = a.originalIndex;
        bVal = b.originalIndex;
      }
            
      if (aVal < bVal) {return jsonlSortDirection === 'asc' ? -1 : 1;}
      if (aVal > bVal) {return jsonlSortDirection === 'asc' ? 1 : -1;}
      return 0;
    });
        
    // Reset to first page when sorting
    jsonlPage = 1;
    populateJsonlTable(filteredJsonlData);
  }
    
  function filterJsonlTable() {
    const typeFilter = document.getElementById('jsonlTypeFilter').value.toLowerCase();
    const searchText = document.getElementById('jsonlSearchInput').value.toLowerCase();
        
    filteredJsonlData = currentJsonlData.filter(line => {
      // Type filter
      if (typeFilter && line.type !== typeFilter) {
        return false;
      }
            
      // Search filter
      if (searchText) {
        const searchableFields = [
          line.type || '',
          line.content || '',
          line.uuid || '',
          line.session_id || '',
          JSON.stringify(line)
        ];
                
        const contentPreview = getJsonlContentPreview(line).toLowerCase();
        searchableFields.push(contentPreview);
                
        const matches = searchableFields.some(field => 
          field.toLowerCase().includes(searchText)
        );
                
        if (!matches) {return false;}
      }
            
      return true;
    });
        
    // Reset to first page when filtering
    jsonlPage = 1;
        
    // Update counts
    document.getElementById('jsonlFilteredCount').textContent = filteredJsonlData.length;
        
    // Re-populate table
    populateJsonlTable(filteredJsonlData);
  }
    
  function showJsonlError(message) {
    document.getElementById('jsonlError').textContent = message;
    document.getElementById('jsonlError').style.display = 'block';
  }
    
  function displayJsonlMetadata(metadata, filename) {
    document.getElementById('jsonlMetadata').style.display = 'block';
        
    // Session ID
    const sessionSpan = document.createElement('span');
    sessionSpan.textContent = metadata.session_id || 'N/A';
    sessionSpan.style.fontFamily = 'monospace';
    sessionSpan.style.fontSize = '0.8rem';
        
    // Created date
    if (metadata.created) {
      const created = new Date(metadata.created * 1000);
      document.getElementById('jsonlCreated').textContent = created.toLocaleString();
    } else {
      document.getElementById('jsonlCreated').textContent = '-';
    }
        
    // Modified date
    if (metadata.modified) {
      const modified = new Date(metadata.modified * 1000);
      document.getElementById('jsonlUpdated').textContent = modified.toLocaleString();
    } else {
      document.getElementById('jsonlUpdated').textContent = '-';
    }
        
    // Duration
    if (metadata.duration_minutes) {
      const hours = Math.floor(metadata.duration_minutes / 60);
      const minutes = Math.round(metadata.duration_minutes % 60);
      if (hours > 0) {
        document.getElementById('jsonlDuration').textContent = `${hours}h ${minutes}m`;
      } else {
        document.getElementById('jsonlDuration').textContent = `${minutes}m`;
      }
    } else {
      document.getElementById('jsonlDuration').textContent = '-';
    }
        
    // File size
    if (metadata.file_size) {
      const size = metadata.file_size;
      let sizeText;
      if (size > 1024 * 1024) {
        sizeText = (size / (1024 * 1024)).toFixed(2) + ' MB';
      } else if (size > 1024) {
        sizeText = (size / 1024).toFixed(2) + ' KB';
      } else {
        sizeText = size + ' bytes';
      }
      document.getElementById('jsonlFileSize').textContent = sizeText;
    } else {
      document.getElementById('jsonlFileSize').textContent = '-';
    }
        
    // Add working directory if available
    if (metadata.working_directory) {
      const wdDiv = document.querySelector('#jsonlMetadata .metadata-grid');
      if (wdDiv && !document.getElementById('jsonlWorkingDir')) {
        const wdContainer = document.createElement('div');
        wdContainer.innerHTML = `
                    <strong class="metadata-label">Working Directory:</strong><br>
                    <span id="jsonlWorkingDir" class="metadata-value mono">${escapeHtml(metadata.working_directory)}</span>
                `;
        wdDiv.appendChild(wdContainer);
      }
    }
  }
    
  function goToJsonlRow() {
    const input = document.getElementById('jsonl-row-input');
    const rowNum = parseInt(input.value);
    if (!rowNum || rowNum < 1) {
      alert('Please enter a valid row number');
      return;
    }
        
    // Check if row exists in original data
    if (rowNum > currentJsonlData.length) {
      alert(`Row ${rowNum} does not exist. Total rows: ${currentJsonlData.length}`);
      return;
    }
        
    // Find the row in filtered data
    const targetLine = filteredJsonlData.find(line => line.originalIndex === rowNum - 1);
    if (!targetLine) {
      // Row is filtered out, ask user if they want to clear filters
      if (confirm(`Row ${rowNum} is currently filtered out. Clear filters to show it?`)) {
        document.getElementById('jsonlTypeFilter').value = '';
        document.getElementById('jsonlSearchInput').value = '';
        filterJsonlTable();
                
        // After clearing filters, use goToRowInPaginatedTable
        setTimeout(() => {
          goToRowInPaginatedTable({
            inputId: 'jsonl-row-input',
            dataArray: filteredJsonlData,
            itemsPerPage: jsonlPerPage,
            navigateFunction: (page) => {
              jsonlPage = page;
              populateJsonlTable(filteredJsonlData);
            },
            tbodySelector: '#jsonlTableBody'
          });
        }, 100);
      }
      return;
    }
        
    // Use goToRowInPaginatedTable for navigation
    // First find the index in filtered data
    const filteredIndex = filteredJsonlData.findIndex(line => line.originalIndex === rowNum - 1);
    if (filteredIndex !== -1) {
      // Temporarily set the input value to the filtered index + 1
      const originalValue = input.value;
      input.value = filteredIndex + 1;
            
      goToRowInPaginatedTable({
        inputId: 'jsonl-row-input',
        dataArray: filteredJsonlData,
        itemsPerPage: jsonlPerPage,
        navigateFunction: (page) => {
          jsonlPage = page;
          populateJsonlTable(filteredJsonlData);
        },
        tbodySelector: '#jsonlTableBody'
      });
            
      // Restore original value
      input.value = originalValue;
    }
  }
    
  // Pagination functions
  function changePageBy(delta) {
    const totalPages = Math.ceil(filteredJsonlData.length / jsonlPerPage);
    jsonlPage = Math.max(1, Math.min(totalPages, jsonlPage + delta));
    populateJsonlTable(filteredJsonlData);
  }
    
  function goToPage() {
    const input = document.getElementById('jsonl-page-input');
    const totalPages = Math.ceil(filteredJsonlData.length / jsonlPerPage);
    jsonlPage = Math.max(1, Math.min(totalPages, parseInt(input.value) || 1));
    populateJsonlTable(filteredJsonlData);
  }
    
  function updatePerPage() {
    const select = document.getElementById('jsonl-per-page');
    jsonlPerPage = parseInt(select.value);
    jsonlPage = 1; // Reset to first page
    populateJsonlTable(filteredJsonlData);
  }
    
  // Public API
  return {
    init: function() {
      // Initialize event listeners if needed
    },
        
    loadFileList: loadJsonlFileList,
    loadFile: loadJsonlFile,
    showDetails: showJsonlDetails,
    sort: sortJsonlTable,
    filter: filterJsonlTable,
    goToRow: goToJsonlRow,
        
    // Pagination functions
    changePageBy: changePageBy,
    goToPage: goToPage,
    updatePerPage: updatePerPage,
        
    // Expose data for other modules if needed
    getCurrentData: function() {
      return currentJsonlData;
    },
        
    getFilteredData: function() {
      return filteredJsonlData;
    }
  };
})();

// Make it available globally
window.JsonlViewer = JsonlViewer;