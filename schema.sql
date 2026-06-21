-- schema.sql
-- Run this file once to create the database and the two tables.
-- In a terminal:  mysql -u root -p < schema.sql

-- 1) Create the database (only if it does not already exist).
CREATE DATABASE IF NOT EXISTS expense_tracker_db;

-- 2) Switch to using it.
USE expense_tracker_db;

-- 3) The users table holds one row per registered person.
CREATE TABLE IF NOT EXISTS users (
    id            INT PRIMARY KEY AUTO_INCREMENT,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4) The transactions table holds every income/expense entry.
--    Each row is linked to one user through user_id (a foreign key).
CREATE TABLE IF NOT EXISTS transactions (
    id               INT PRIMARY KEY AUTO_INCREMENT,
    user_id          INT NOT NULL,
    type             ENUM('Income', 'Expense') NOT NULL,
    amount           DECIMAL(10, 2) NOT NULL,
    category         VARCHAR(100) NOT NULL,
    description      VARCHAR(255),
    transaction_date DATE NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
