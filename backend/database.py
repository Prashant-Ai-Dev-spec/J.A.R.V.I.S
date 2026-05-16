"""
Minimal database module for J.A.R.V.I.S Cowork.

Provides a SessionLocal factory used by execute_tool().
The computer_use tool doesn't need a real DB session, but the
_create_completion call signature passes one in, so we provide
a lightweight stub that can be upgraded to a real SQLAlchemy
session when the full backend models are added.
"""

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, declarative_base

    import os
    _DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis.db")
    _DB_URL = f"sqlite:///{_DB_PATH}"

    engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

except ImportError:
    # SQLAlchemy not installed — provide a no-op stub so imports don't break
    class _StubSession:
        def close(self):
            pass

    def SessionLocal():
        return _StubSession()
