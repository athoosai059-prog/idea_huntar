import os
from pathlib import Path
from dotenv import load_dotenv

# Load from .env file at the root of the project
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
    TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
    
    CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
    CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "llama3.3-70b")
    
    # "gemini", "anthropic", "groq", "together", or "cerebras"
    PRIMARY_AI = os.getenv("PRIMARY_AI", "groq")
    
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "IdeaHunter:v1.0")
    
    PRODUCTHUNT_TOKEN = os.getenv("PRODUCTHUNT_TOKEN", "")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
    
    SCRAPE_SCHEDULE = os.getenv("SCRAPE_SCHEDULE", "0 6 * * *")
    MIN_IDEA_SCORE = float(os.getenv("MIN_IDEA_SCORE", "6.0"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
    TARGET_KEYWORDS = os.getenv("TARGET_KEYWORDS", "")

    def reload(self):
        load_dotenv(dotenv_path=env_path, override=True)
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
        self.CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
        self.PRIMARY_AI = os.getenv("PRIMARY_AI", "groq")
        self.MIN_IDEA_SCORE = float(os.getenv("MIN_IDEA_SCORE", "6.0"))
        self.TARGET_KEYWORDS = os.getenv("TARGET_KEYWORDS", "")

settings = Settings()
