-- ============================================
-- Database schema for the orders demo
-- Run this against your PostgreSQL instance
-- ============================================

CREATE TABLE IF NOT EXISTS customers (
    id      SERIAL PRIMARY KEY,
    name    TEXT    NOT NULL,
    email   TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS orders (
    id            SERIAL PRIMARY KEY,
    customer_id   INT         NOT NULL REFERENCES customers(id),
    order_date    DATE        NOT NULL DEFAULT CURRENT_DATE,
    total_amount  NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    status        TEXT        NOT NULL DEFAULT 'pending'
);

-- Index for the common query pattern used by the MCP tool
CREATE INDEX IF NOT EXISTS idx_orders_customer_amount
    ON orders (customer_id, total_amount DESC, order_date DESC);
