ALTER TABLE team_survey_responses
    ADD COLUMN IF NOT EXISTS brew_drinking_level TEXT,
    ADD COLUMN IF NOT EXISTS beers_pledged INTEGER,
    ADD COLUMN IF NOT EXISTS score_prediction_riks INTEGER,
    ADD COLUMN IF NOT EXISTS score_prediction_wades INTEGER,
    ADD COLUMN IF NOT EXISTS first_to_puke TEXT,
    ADD COLUMN IF NOT EXISTS first_to_tap_out TEXT;

CREATE TABLE IF NOT EXISTS erik_dossier_responses (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL UNIQUE REFERENCES people(id),
    best_erik_story TEXT,
    erik_in_one_word TEXT,
    eriks_nickname TEXT,
    over_under_marriage TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
