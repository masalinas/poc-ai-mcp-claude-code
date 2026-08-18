-- ============================================
-- Sample data for local testing
-- Safe to run multiple times (skip on conflict)
-- ============================================

INSERT INTO customers (name, email) VALUES
    ('Ana García',      'ana@example.com'),
    ('Carlos López',    'carlos@example.com'),
    ('Elena Martínez',  'elena@example.com')
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
    -- Ana's orders
    (1, '2025-01-10', 250.00,  'completed'),
    (1, '2025-02-14', 75.50,   'completed'),
    (1, '2025-03-01', 520.00,  'shipped'),
    (1, '2025-04-20', 95.00,   'cancelled'),
    (1, '2025-06-15', 180.75,  'completed'),

    -- Carlos's orders
    (2, '2025-02-01', 340.00,  'completed'),
    (2, '2025-03-15', 12.99,   'pending'),
    (2, '2025-05-10', 890.00,  'shipped'),

    -- Elena's orders
    (3, '2025-04-01', 67.00,   'completed'),
    (3, '2025-05-22', 310.50,  'completed'),
    (3, '2025-07-08', 1000.00, 'pending')
ON CONFLICT DO NOTHING;
