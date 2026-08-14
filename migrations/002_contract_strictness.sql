ALTER TABLE contracts ADD COLUMN strictness TEXT NOT NULL DEFAULT 'strict'
    CHECK (strictness IN ('strict', 'lenient'));

ALTER TABLE run_diffs ADD COLUMN severity TEXT NOT NULL DEFAULT 'drift'
    CHECK (severity IN ('drift', 'notice'));
