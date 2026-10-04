ALTER TABLE webhook_events
  ADD COLUMN delivery_key VARCHAR(128);

UPDATE webhook_events
SET delivery_key = encode(
    digest(platform::text || ':' || COALESCE(signature, '') || ':' || payload, 'sha256'),
    'hex'
  )
WHERE delivery_key IS NULL;

ALTER TABLE webhook_events ALTER COLUMN delivery_key SET NOT NULL;
CREATE UNIQUE INDEX uq_webhook_delivery_key ON webhook_events(delivery_key);
