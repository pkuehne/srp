CREATE TABLE lossmails (
    loss_id INTEGER PRIMARY KEY,
    loss_hash STRING,
    character_id INTEGER,
    character_name STRING,
    ship_id INTEGER,
    ship_type STRING,
    system_id INTEGER,
    system_name STRING,
    claimed BOOLEAN,
    status STRING
);
