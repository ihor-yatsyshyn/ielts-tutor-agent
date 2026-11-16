import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import config
from db.models import Base

_engine = None
_Session = None


def init_db(url: str | None = None) -> None:
    """Створює engine і таблиці. Для тестів: init_db('sqlite:///:memory:')."""
    global _engine, _Session
    url = url or config.DATABASE_URL
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        else:
            path = url.replace("sqlite:///", "", 1)
            if os.path.dirname(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
    _engine = create_engine(url, **kwargs)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(_engine, expire_on_commit=False)


@contextmanager
def session_scope():
    if _Session is None:
        init_db()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
