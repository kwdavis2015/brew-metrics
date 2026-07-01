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
    brew_drinking_level TEXT,
    notes TEXT,
    beers_pledged INTEGER,
    score_prediction_red INTEGER,
    score_prediction_blue INTEGER,
    first_to_puke TEXT,
    first_to_tap_out TEXT,
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
    event_type TEXT NOT NULL DEFAULT 'single' CHECK (event_type IN ('single', 'best_of_3')),
    category TEXT NOT NULL DEFAULT 'main' CHECK (category IN ('main', 'flong', 'misc_friday', 'misc_saturday', 'computed')),
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

CREATE TABLE IF NOT EXISTS event_round_results (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES event_master(id),
    round_number INTEGER NOT NULL CHECK (round_number IN (1, 2, 3)),
    winner_team TEXT NOT NULL REFERENCES teams(name),
    entered_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (event_id, round_number)
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

-- Seed event catalog — DO UPDATE so new event_type/category values apply on re-run
INSERT INTO event_master (name, points_available, event_type, category) VALUES
-- Main events (400 pts total)
    ('Escanaba',        100, 'single',    'main'),
    ('Flong Round 1',    50, 'single',    'flong'),
    ('Flong Round 2',    50, 'single',    'flong'),
    ('Keg Race',        100, 'single',    'main'),
    ('Relay',           100, 'single',    'main'),
-- Beers Drank: 0.4 pts/beer, computed dynamically; points_available is max reference only
    ('Beers Drank',     400, 'single',    'computed'),
-- Friday misc events (100 pts total)
    ('Billiards',        20, 'best_of_3', 'misc_friday'),
    ('Cornhole',         20, 'best_of_3', 'misc_friday'),
    ('Shuffleboard',     20, 'best_of_3', 'misc_friday'),
    ('Foosball',         20, 'best_of_3', 'misc_friday'),
    ('Darts',            10, 'best_of_3', 'misc_friday'),
    ('Jenga',            10, 'best_of_3', 'misc_friday'),
-- Saturday misc events (100 pts total)
    ('Golf Simulator',   20, 'best_of_3', 'misc_saturday'),
    ('Pool Basketball',  20, 'best_of_3', 'misc_saturday'),
    ('Beersbee',         20, 'best_of_3', 'misc_saturday'),
    ('Connect 4',        20, 'best_of_3', 'misc_saturday'),
    ('Golden Tee',       10, 'best_of_3', 'misc_saturday'),
    ('Joust',            10, 'best_of_3', 'misc_saturday')
ON CONFLICT (name) DO UPDATE SET
    event_type = EXCLUDED.event_type,
    category   = EXCLUDED.category;

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO app_settings (key, value)
    VALUES ('weekend_started', 'false')
ON CONFLICT (key) DO NOTHING;
