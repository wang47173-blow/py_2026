from __future__ import annotations

from alembic import command
from alembic.config import Config

from app.config import settings


def run_migrations() -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
