-- ============================================================
-- CivicIQ — Database Initialization Script
-- Run this once before starting services
-- MySQL user:  | password: 
-- ============================================================

CREATE DATABASE IF NOT EXISTS civic_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE civic_platform;

-- ── Users Table ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(255) NOT NULL,
    phone            VARCHAR(20) NOT NULL UNIQUE,
    credibilityScore DECIMAL(4,3) NOT NULL DEFAULT 0.500,
    validatedCount   INT NOT NULL DEFAULT 0,
    rejectedCount    INT NOT NULL DEFAULT 0,
    createdAt        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Complaints Table ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS complaints (
    id                  VARCHAR(36) PRIMARY KEY,
    category            ENUM('ROAD_DAMAGE','WATER_LEAKAGE','STREETLIGHT','TRAFFIC_SIGNAL','SEWERAGE','GARBAGE','TREE_FALL','OTHER') DEFAULT NULL,
    department          ENUM('ROADS','WATER','ELECTRICITY','TRAFFIC','SANITATION','SEWER','PARKS','OTHER') DEFAULT NULL,
    description         TEXT NOT NULL,
    imageUrl            TEXT DEFAULT NULL,
    latitude            DECIMAL(10,8) NOT NULL,
    longitude           DECIMAL(11,8) NOT NULL,
    priorityScore       DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    severityScore       DECIMAL(4,3) NOT NULL DEFAULT 0.000,
    communityValidation DECIMAL(4,3) NOT NULL DEFAULT 0.000,
    reporterCredibility DECIMAL(4,3) NOT NULL DEFAULT 0.500,
    estimatedCost       INT NOT NULL DEFAULT 0,
    estimatedDuration   VARCHAR(100) DEFAULT NULL,
    summary             TEXT DEFAULT NULL,
    status              ENUM('PROCESSING','VALID','IN_PROGRESS','RESOLVED','REJECTED') NOT NULL DEFAULT 'PROCESSING',
    reporterName        VARCHAR(255) NOT NULL,
    reporterPhone       VARCHAR(20) NOT NULL,
    isDuplicate         BOOLEAN NOT NULL DEFAULT FALSE,
    parentComplaintId   VARCHAR(36) DEFAULT NULL,
    createdAt           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parentComplaintId) REFERENCES complaints(id) ON DELETE SET NULL,
    INDEX idx_complaints_status (status),
    INDEX idx_complaints_category (category),
    INDEX idx_complaints_department (department),
    INDEX idx_complaints_priority (priorityScore DESC),
    INDEX idx_complaints_created (createdAt DESC),
    INDEX idx_complaints_phone (reporterPhone),
    INDEX idx_complaints_location (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Complaint Reporters Junction Table ────────────────────
CREATE TABLE IF NOT EXISTS complaint_reporters (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    complaintId VARCHAR(36) NOT NULL,
    userId      INT NOT NULL,
    reportedAt  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaintId) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_complaint_user (complaintId, userId),
    INDEX idx_cr_complaint (complaintId),
    INDEX idx_cr_user (userId)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Verify ────────────────────────────────────────────────
SHOW TABLES;
SELECT 'Database initialized successfully!' AS message;
