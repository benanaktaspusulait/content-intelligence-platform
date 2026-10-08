CREATE TABLE consumer_service_marker (
    id INTEGER PRIMARY KEY,
    marker VARCHAR(40) NOT NULL
);

INSERT INTO consumer_service_marker (id, marker) VALUES (1, 'consumer-v1');
