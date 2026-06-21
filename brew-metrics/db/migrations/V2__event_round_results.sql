-- Add event categorization and per-round result tracking for best-of-3 games.
--
-- event_type: 'single' (pick a winner once) | 'best_of_3' (track up to 3 rounds)
-- category:   groups events for UI display and point accounting
--
-- ADD COLUMN IF NOT EXISTS makes these statements safe to replay if they were
-- previously applied outside the migration system.

ALTER TABLE event_master
    ADD COLUMN IF NOT EXISTS event_type TEXT NOT NULL DEFAULT 'single'
        CHECK (event_type IN ('single', 'best_of_3')),
    ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'main'
        CHECK (category IN ('main', 'flong', 'misc_friday', 'misc_saturday', 'computed'));

CREATE TABLE IF NOT EXISTS event_round_results (
    id           SERIAL PRIMARY KEY,
    event_id     INTEGER NOT NULL REFERENCES event_master(id),
    round_number INTEGER NOT NULL CHECK (round_number IN (1, 2, 3)),
    winner_team  TEXT NOT NULL REFERENCES teams(name),
    entered_by   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (event_id, round_number)
);

-- Classify all seeded events
UPDATE event_master SET event_type = 'single', category = 'main'
    WHERE name IN ('Escanaba', 'Keg Race', 'Relay');

UPDATE event_master SET event_type = 'single', category = 'flong'
    WHERE name IN ('Flong Round 1', 'Flong Round 2');

UPDATE event_master SET event_type = 'single', category = 'computed'
    WHERE name = 'Beers Drank';

UPDATE event_master SET event_type = 'best_of_3', category = 'misc_friday'
    WHERE name IN ('Billiards', 'Cornhole', 'Shuffleboard', 'Foosball', 'Darts', 'Jenga');

UPDATE event_master SET event_type = 'best_of_3', category = 'misc_saturday'
    WHERE name IN ('Golf Simulator', 'Pool Basketball', 'Beersbee', 'Connect 4', 'Golden Tee', 'Joust');
