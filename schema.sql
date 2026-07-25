CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    lutris_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,

    steam_appid TEXT,
    steam_url TEXT,

    unavailable INTEGER DEFAULT 0,

    last_checked TEXT
);


CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    game_id INTEGER NOT NULL,

    title TEXT,
    description TEXT,
    update_date TEXT,
    link TEXT,
    notes TEXT,

    UNIQUE(game_id, link),

    FOREIGN KEY(game_id)
        REFERENCES games(id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
