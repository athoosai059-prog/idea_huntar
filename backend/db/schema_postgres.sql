CREATE TABLE IF NOT EXISTS raw_posts (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata TEXT,
  collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ideas (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  pain_point TEXT,
  source TEXT,
  source_ref TEXT,
  keywords TEXT,
  score_overall REAL,
  score_demand INTEGER,
  score_competition INTEGER,
  score_trend INTEGER,
  score_uniqueness INTEGER,
  saved INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deep_research (
    id SERIAL PRIMARY KEY,
    idea_id INTEGER,
    type TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (idea_id) REFERENCES ideas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS run_log (
  id SERIAL PRIMARY KEY,
  run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  source TEXT,
  records_collected INTEGER,
  ideas_found INTEGER,
  status TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS demand_metrics (
  id SERIAL PRIMARY KEY,
  idea_id INTEGER,
  search_volume INTEGER,
  keyword_difficulty INTEGER,
  cpc REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (idea_id) REFERENCES ideas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gsc_metrics (
  id SERIAL PRIMARY KEY,
  idea_id INTEGER,
  impressions INTEGER,
  clicks INTEGER,
  position REAL,
  ctr REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (idea_id) REFERENCES ideas(id) ON DELETE CASCADE
);
