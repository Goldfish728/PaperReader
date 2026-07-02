from sqlmodel import Session, SQLModel, create_engine

from backend.app.core.paths import database_path


def get_engine():
    path = database_path()
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def init_db() -> None:
    # Import models so SQLModel metadata is populated before create_all.
    import backend.app.db.models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


def get_session():
    with Session(get_engine()) as session:
        yield session
