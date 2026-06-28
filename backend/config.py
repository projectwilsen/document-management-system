from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    dashboard_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
