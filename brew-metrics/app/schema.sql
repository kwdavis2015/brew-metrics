CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO teams (name) VALUES ('Riks'), ('Wades')
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
    capacity INTEGER NOT NULL DEFAULT 330,
    finished_at TIMESTAMPTZ
);

INSERT INTO team_keg_state (team_name) VALUES ('Riks'), ('Wades')
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

-- Seed event catalog
INSERT INTO event_master (name, points_available) VALUES
    ('Cornhole Tournament', 100),
    ('Flip Cup', 75),
    ('Trivia Night', 100),
    ('Billiards', 75),
    ('Giant Jenga', 50),
    ('Brew Cup', 200),
    ('Flong Night 1', 75),
    ('Flong Night 2', 75),
    ('Keg Race', 100),
    ('Brewsby', 75),
    ('Darts', 50),
    ('Shuffleboard', 50),
    ('Golf Sim', 75),
    ('Arcade Games', 50),
    ('Giant Connect 4', 50),
    ('Pool Basketball', 50)
ON CONFLICT (name) DO NOTHING;
