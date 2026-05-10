from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    GITHUB_PAT: str
    HF_TOKEN: str
    JWT_SECRET: str
    MLFLOW_TRACKING_URI: str
    REDIS_URL: str
    CHROMA_PERSIST_DIR: str
    FEAST_REPO_PATH: str
    OLLAMA_BASE_URL: str
    
    # Model Selection (Cascade: fast primary → smart fallback)
    OLLAMA_LLM_MODEL: str = "gemma2:2b"
    OLLAMA_FALLBACK_MODEL: str = "gemma4:e4b"
    OLLAMA_EMBED_MODEL: str = "bge-m3:latest"

    # Configuration for pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra environment variables
    )

# Create a singleton instance of settings
settings = Settings()
