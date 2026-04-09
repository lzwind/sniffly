// Constants for Claude Analytics

// User interruption patterns
const USER_INTERRUPTION_PREFIX = '[Request interrupted by user for tool use]';
const USER_INTERRUPTION_API_ERROR = 'API Error: Request was aborted.';
const USER_INTERRUPTION_PATTERNS = [
  USER_INTERRUPTION_PREFIX,
  USER_INTERRUPTION_API_ERROR
];

// Pagination defaults
const DEFAULT_MESSAGES_PER_PAGE = 20;
const DEFAULT_COMMANDS_PER_PAGE = 20;

// Chart colors
const CHART_COLORS = {
  primary: '#667eea',
  secondary: '#764ba2',
  success: '#48bb78',
  warning: '#ed8936',
  danger: '#f56565',
  info: '#4299e1'
};

// Claude logs location info
const CLAUDE_LOGS_TOOLTIP = `<div class="example">
    <strong>Example:</strong><br>
    Project: /Users/john/dev/myapp<br>
    Logs at: ~/.claude/projects/-Users-john-dev-myapp/
</div>`;

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    USER_INTERRUPTION_PREFIX,
    USER_INTERRUPTION_API_ERROR,
    USER_INTERRUPTION_PATTERNS,
    DEFAULT_MESSAGES_PER_PAGE,
    DEFAULT_COMMANDS_PER_PAGE,
    CHART_COLORS,
    CLAUDE_LOGS_TOOLTIP
  };
}