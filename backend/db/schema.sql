CREATE TABLE IF NOT EXISTS raw_posts (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,          -- 'reddit', 'playstore', 'trends', 'hn', 'ph'
  content TEXT NOT NULL,
  metadata TEXT,                 -- JSON: upvotes, subreddit, app_name, etc.
  collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ideas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  pain_point TEXT,
  source TEXT,
  source_ref TEXT,               -- subreddit name, app id, etc.
  keywords TEXT,                 -- JSON array
  score_overall REAL,
  score_demand INTEGER,
  score_competition INTEGER,
  score_trend INTEGER,
  score_uniqueness INTEGER,
  saved INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS deep_research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id INTEGER,
    type TEXT, -- 'competitors' or 'playbook'
    content TEXT, -- JSON or Markdown content
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (idea_id) REFERENCES ideas(id)
);

CREATE TABLE IF NOT EXISTS run_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  source TEXT,
  records_collected INTEGER,
  ideas_found INTEGER,
  status TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS demand_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idea_id INTEGER,
  search_volume INTEGER,
  keyword_difficulty INTEGER,
  cpc REAL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (idea_id) REFERENCES ideas(id)
);

CREATE TABLE IF NOT EXISTS gsc_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idea_id INTEGER,
  impressions INTEGER,
  clicks INTEGER,
  position REAL,
  ctr REAL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (idea_id) REFERENCES ideas(id)
);
