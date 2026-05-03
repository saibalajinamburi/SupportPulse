from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    GITHUB_PAT: str
    HF_TOKEN: str
    GROQ_API_KEY: str | None = None
    JWT_SECRET: str
    MLFLOW_TRACKING_URI: str
    REDIS_URL: str
    CHROMA_PERSIST_DIR: str
    FEAST_REPO_PATH: str
    OLLAMA_BASE_URL: str

    # Configuration for pydantic-settings
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra environment variables
    )

# Create a singleton instance of settings
settings = Settings()
