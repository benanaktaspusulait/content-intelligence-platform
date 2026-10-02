-- V23: Create notifications table for in-app notifications

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    related_entity_id UUID,
    related_entity_type VARCHAR(50),
    link VARCHAR(500),
    priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for common queries
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_priority ON notifications(priority);
CREATE INDEX idx_notifications_related_entity ON notifications(related_entity_id, related_entity_type);

-- Composite index for unread high-priority notifications
CREATE INDEX idx_notifications_unread_high_priority 
    ON notifications(is_read, priority, created_at DESC) 
    WHERE is_read = FALSE AND priority IN ('HIGH', 'URGENT');
