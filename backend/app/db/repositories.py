from sqlmodel import Session, select

from backend.app.db.models import AppSetting


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_value(self, key: str) -> str | None:
        setting = self.session.get(AppSetting, key)
        return setting.value if setting else None

    def set_value(self, key: str, value: str) -> None:
        setting = self.session.get(AppSetting, key)
        if setting is None:
            setting = AppSetting(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
            self.session.add(setting)

    def list_all(self) -> dict[str, str]:
        rows = self.session.exec(select(AppSetting)).all()
        return {row.key: row.value for row in rows}
