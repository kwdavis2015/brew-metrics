-- Baseline schema: all tables and seed data as established in the initial release.
-- All statements are idempotent (IF NOT EXISTS / ON CONFLICT DO NOTHING) so this
-- migration is safe to apply against a DB that was already bootstrapped manually.

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO teams (name) VALUES ('Red'), ('Blue')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL UNIQUE,
    nickname TEXT,
    team_name TEXT REFERENCES teams(name),
    status TEXT NOT NULL DEFAULT 'pre_registered' CHECK (status IN ('pre_registered', 'active')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_survey_responses (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL UNIQUE REFERENCES people(id),
    expected_arrival_day TEXT NOT NULL,
    expected_arrival_time TEXT,
    expected_departure_day TEXT,
    expected_departure_time TEXT,
    skill_1 TEXT,
    skill_2 TEXT,
    skill_3 TEXT,
    brew_drinking_skill_rank INTEGER NOT NULL DEFAULT 2 CHECK (brew_drinking_skill_rank IN (1, 2, 3)),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brew_log (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id),
    team_name TEXT NOT NULL REFERENCES teams(name),
    source TEXT NOT NULL DEFAULT 'keg' CHECK (source IN ('keg', 'byob')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'reversed')),
    reversal_of_entry_id INTEGER REFERENCES brew_log(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_keg_state (
    team_name TEXT PRIMARY KEY REFERENCES teams(name),
    finished_at TIMESTAMPTZ
);

INSERT INTO team_keg_state (team_name) VALUES ('Red'), ('Blue')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS event_master (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed')),
    points_available INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_results (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL UNIQUE REFERENCES event_master(id),
    team_1_points INTEGER NOT NULL DEFAULT 0,
    team_2_points INTEGER NOT NULL DEFAULT 0,
    entered_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_adjustments (
    id SERIAL PRIMARY KEY,
    adjustment_type TEXT NOT NULL,
    team_name TEXT REFERENCES teams(name),
    person_id INTEGER REFERENCES people(id),
    amount INTEGER,
    related_entry_id INTEGER REFERENCES brew_log(id),
    reason TEXT NOT NULL,
    entered_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO event_master (name, points_available) VALUES
    ('Escanaba',       100),
    ('Flong Round 1',   50),
    ('Flong Round 2',   50),
    ('Keg Race',       100),
    ('Relay',          100),
    ('Beers Drank',    400),
    ('Billiards',       20),
    ('Cornhole',        20),
    ('Shuffleboard',    20),
    ('Foosball',        20),
    ('Darts',           10),
    ('Jenga',           10),
    ('Golf Simulator',  20),
    ('Pool Basketball', 20),
    ('Beersbee',        20),
    ('Connect 4',       20),
    ('Golden Tee',      10),
    ('Joust',           10)
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO app_settings (key, value)
    VALUES ('weekend_started', 'false')
ON CONFLICT (key) DO NOTHING;
