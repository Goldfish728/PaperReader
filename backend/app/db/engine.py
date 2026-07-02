from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.paths import database_path

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        path = database_path()
        _engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    return _engine


def reset_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def init_db() -> None:
    # Import models so SQLModel metadata is populated before create_all.
    import backend.app.db.models  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        from backend.app.db.fts import init_fts

        init_fts(session)


def get_session():
    with Session(get_engine()) as session:
        yield session
