CREATE TABLE losses (
    id INTEGER PRIMARY KEY,
    hash STRING,
    is_loss BOOLEAN,
    character_id INTEGER,
    character_name STRING,
    ship_type_id INTEGER,
    ship_type_name STRING,
    system_id INTEGER,
    system_name STRING,
    timestamp DATETIME,
    status STRING
);
