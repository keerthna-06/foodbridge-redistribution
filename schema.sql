PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS workspace (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS food (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    organization TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    category TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    cold_chain INTEGER NOT NULL CHECK (cold_chain IN (0, 1))
);
CREATE TABLE IF NOT EXISTS recipients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    category TEXT NOT NULL,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 3),
    x REAL NOT NULL,
    y REAL NOT NULL,
    cold_storage INTEGER NOT NULL CHECK (cold_storage IN (0, 1))
);
CREATE TABLE IF NOT EXISTS deliveries (
    id TEXT PRIMARY KEY,
    food_id TEXT NOT NULL REFERENCES food(id),
    recipient_id TEXT NOT NULL REFERENCES recipients(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    status TEXT NOT NULL CHECK (status IN ('Reserved','Picked up','Delivered','Cancelled')),
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload TEXT NOT NULL
);
