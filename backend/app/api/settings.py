from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.app.core.config import get_settings
from backend.app.db.engine import get_session
from backend.app.db.repositories import SettingsRepository
from backend.app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])
SessionDependency = Annotated[Session, Depends(get_session)]


def resolved_settings(session: Session) -> SettingsRead:
    env = get_settings()
    repo = SettingsRepository(session)
    values = repo.list_all()
    api_key = values.get("api_key", env.api_key)
    return SettingsRead(
        api_base_url=values.get("api_base_url", env.api_base_url),
        chat_model=values.get("chat_model", env.chat_model),
        request_timeout_seconds=int(
            values.get("request_timeout_seconds", env.request_timeout_seconds)
        ),
        temperature=float(values.get("temperature", env.temperature)),
        api_key_configured=bool(api_key),
    )


@router.get("", response_model=SettingsRead)
def read_settings(session: SessionDependency) -> SettingsRead:
    return resolved_settings(session)


@router.put("", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate, session: SessionDependency) -> SettingsRead:
    repo = SettingsRepository(session)
    repo.set_value("api_base_url", payload.api_base_url)
    repo.set_value("api_key", payload.api_key)
    repo.set_value("chat_model", payload.chat_model)
    repo.set_value("request_timeout_seconds", str(payload.request_timeout_seconds))
    repo.set_value("temperature", str(payload.temperature))
    session.commit()
    return resolved_settings(session)
