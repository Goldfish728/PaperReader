from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    api_base_url: str = Field(min_length=1)
    api_key: str = Field(default="")
    chat_model: str = Field(min_length=1)
    request_timeout_seconds: int = Field(default=120, ge=5, le=600)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class SettingsRead(BaseModel):
    api_base_url: str
    chat_model: str
    request_timeout_seconds: int
    temperature: float
    api_key_configured: bool
