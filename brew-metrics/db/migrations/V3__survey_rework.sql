ALTER TABLE team_survey_responses
    ADD COLUMN IF NOT EXISTS brew_drinking_level TEXT,
    ADD COLUMN IF NOT EXISTS beers_pledged INTEGER,
    ADD COLUMN IF NOT EXISTS score_prediction_red INTEGER,
    ADD COLUMN IF NOT EXISTS score_prediction_blue INTEGER,
    ADD COLUMN IF NOT EXISTS first_to_puke TEXT,
    ADD COLUMN IF NOT EXISTS first_to_tap_out TEXT;
