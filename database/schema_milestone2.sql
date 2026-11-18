-- SafeSight AI - Milestone 2: Document Intelligence and Knowledge Base Schema
-- Tables use CREATE TABLE IF NOT EXISTS to guarantee safe, non-destructive migration.

-- 1. Repositories (Collections of Documents)
CREATE TABLE IF NOT EXISTS repositories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Documents
CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    repository_id INT,
    original_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size INT DEFAULT 0,
    doc_type ENUM('inspection_report', 'safety_manual', 'sop', 'other') DEFAULT 'other',
    title VARCHAR(255),
    page_count INT DEFAULT 1,
    status ENUM('uploaded', 'processing', 'processed', 'needs review', 'verified', 'failed') DEFAULT 'uploaded',
    progress_percent INT DEFAULT 0,
    error_message TEXT,
    avg_confidence FLOAT DEFAULT 0.0,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME,
    INDEX idx_doc_repo (repository_id),
    INDEX idx_doc_status (status),
    INDEX idx_doc_type (doc_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Document Pages (Page text and OCR flag)
CREATE TABLE IF NOT EXISTS document_pages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    page_no INT NOT NULL,
    text MEDIUMTEXT,
    used_ocr BOOLEAN DEFAULT FALSE,
    INDEX idx_page_doc (document_id),
    CONSTRAINT fk_pages_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Document Sections (Heading hierarchy / outline)
CREATE TABLE IF NOT EXISTS doc_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    parent_id INT DEFAULT NULL,
    title VARCHAR(255) NOT NULL,
    level INT DEFAULT 1,
    page_start INT DEFAULT 1,
    page_end INT DEFAULT 1,
    INDEX idx_sec_doc (document_id),
    CONSTRAINT fk_sections_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Document Chunks (for search & Q&A)
CREATE TABLE IF NOT EXISTS doc_chunks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    repository_id INT,
    section_id INT DEFAULT NULL,
    page_no INT DEFAULT 1,
    chunk_index INT DEFAULT 0,
    text TEXT NOT NULL,
    INDEX idx_chunk_doc (document_id),
    INDEX idx_chunk_repo (repository_id),
    FULLTEXT KEY idx_chunk_text (text),
    CONSTRAINT fk_chunks_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Extracted Inspection Report Header Fields
CREATE TABLE IF NOT EXISTS report_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    field_value TEXT,
    confidence FLOAT DEFAULT 1.0,
    page_no INT DEFAULT 1,
    is_edited BOOLEAN DEFAULT FALSE,
    INDEX idx_rf_doc (document_id),
    CONSTRAINT fk_rf_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Extracted Inspection Report Findings
CREATE TABLE IF NOT EXISTS report_findings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'other',
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'LOW',
    location VARCHAR(255),
    corrective_action TEXT,
    responsible_person VARCHAR(150),
    due_date VARCHAR(50),
    status ENUM('open', 'in progress', 'closed') DEFAULT 'open',
    confidence FLOAT DEFAULT 1.0,
    page_no INT DEFAULT 1,
    INDEX idx_findings_doc (document_id),
    INDEX idx_findings_cat (category),
    INDEX idx_findings_sev (severity),
    CONSTRAINT fk_findings_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Extracted Manual Safety Rules (PPE rules, mandatory requirements)
CREATE TABLE IF NOT EXISTS manual_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    section_id INT DEFAULT NULL,
    rule_text TEXT NOT NULL,
    ppe_type VARCHAR(50) DEFAULT 'other',
    page_no INT DEFAULT 1,
    INDEX idx_mr_doc (document_id),
    INDEX idx_mr_ppe (ppe_type),
    CONSTRAINT fk_rules_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Extracted Manual Procedures (Numbered procedural steps)
CREATE TABLE IF NOT EXISTS manual_procedures (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_id INT NOT NULL,
    section_id INT DEFAULT NULL,
    title VARCHAR(255) NOT NULL,
    steps JSON,
    page_no INT DEFAULT 1,
    INDEX idx_mp_doc (document_id),
    CONSTRAINT fk_proc_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Knowledge Search Logs
CREATE TABLE IF NOT EXISTS search_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    query VARCHAR(255) NOT NULL,
    mode VARCHAR(50) DEFAULT 'hybrid',
    result_count INT DEFAULT 0,
    took_ms FLOAT DEFAULT 0.0,
    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default 3 repositories if they do not exist
INSERT IGNORE INTO repositories (id, name, description) VALUES
(1, 'Inspection Reports', 'Official safety audit and site compliance inspection logs'),
(2, 'Safety Manuals', 'Comprehensive corporate and site PPE safety handbooks'),
(3, 'SOPs', 'Standard Operating Procedures for equipment and hazardous operations');
