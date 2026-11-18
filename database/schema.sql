-- SafeSight AI Database Schema
-- PPE Safety Analytics Platform

CREATE DATABASE IF NOT EXISTS safesight;
USE safesight;

-- 1. Uploads table
CREATE TABLE IF NOT EXISTS uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_type ENUM('image', 'video') NOT NULL,
    file_path TEXT NOT NULL,
    output_path TEXT,
    camera_name VARCHAR(100) DEFAULT 'Manual Upload',
    location VARCHAR(255) DEFAULT 'Zone A - Entrance',
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('processing', 'done', 'failed') DEFAULT 'processing',
    INDEX idx_uploaded_at (uploaded_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Detections table (summary per frame/image)
CREATE TABLE IF NOT EXISTS detections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    upload_id INT,
    frame_no INT DEFAULT 0,
    timestamp_sec FLOAT DEFAULT 0.0,
    total_people INT DEFAULT 0,
    safe_count INT DEFAULT 0,
    unsafe_count INT DEFAULT 0,
    compliance_percent FLOAT DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_upload_id (upload_id),
    INDEX idx_created_at (created_at),
    CONSTRAINT fk_detections_upload
        FOREIGN KEY (upload_id) REFERENCES uploads(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Violations table (individual infraction events)
CREATE TABLE IF NOT EXISTS violations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    upload_id INT,
    detection_id INT,
    violation_type ENUM('helmet', 'vest', 'goggles', 'other') NOT NULL,
    severity ENUM('LOW', 'MEDIUM', 'HIGH') NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    snapshot_path TEXT,
    camera_name VARCHAR(100) DEFAULT 'Cam 01 - Zone A',
    location VARCHAR(255) DEFAULT 'Main Facility',
    status ENUM('detected', 'pending review', 'confirmed', 'dismissed', 'resolved') DEFAULT 'detected',
    reviewed_by VARCHAR(100),
    notes TEXT,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_violation_type (violation_type),
    INDEX idx_severity (severity),
    INDEX idx_status (status),
    INDEX idx_detected_at (detected_at),
    CONSTRAINT fk_violations_upload
        FOREIGN KEY (upload_id) REFERENCES uploads(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_violations_detection
        FOREIGN KEY (detection_id) REFERENCES detections(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Cameras table
CREATE TABLE IF NOT EXISTS cameras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    zone VARCHAR(100) NOT NULL,
    source VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Default cameras
INSERT IGNORE INTO cameras (id, name, zone, source, is_active) VALUES
(1, 'Cam 01 – Zone A', 'Zone A', '0', 1),
(2, 'Cam 02 – Zone B', 'Zone B', 'sample_zone_b.mp4', 1),
(3, 'Cam 03 – Exit', 'Exit Gate', 'sample_exit.mp4', 1);
