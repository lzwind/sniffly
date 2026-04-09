-- Sniffly database initialization script

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Seed default admin user (password: admin123)
-- Hash generated with bcrypt
INSERT INTO users (username, password_hash, is_admin) VALUES
('admin', '$2b$12$hf6g8j1IFicvlZaQH.yLz.CBARDykASKIvr0lVE15g5gkfhbicjqG', TRUE)
ON DUPLICATE KEY UPDATE username=username;

CREATE TABLE IF NOT EXISTS shares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    stats JSON NOT NULL,
    user_commands JSON NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY uix_user_project (user_id, project_name),
    INDEX idx_shares_user_id (user_id)
);
