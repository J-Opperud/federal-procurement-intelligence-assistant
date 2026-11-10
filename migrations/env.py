"""Alembic environment for Sentinel Scout schema migrations."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app import models  # noqa: F401 - register all mapped tables

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the migration database URL from alembic.ini.
target_metadata = Base.metadata

def render_item(type_, obj, autogen_context):
    """Render custom SQLAlchemy types using their underlying database types."""

    if type_ == "type" and isinstance(obj, models.UTCDateTime):
        return "sa.DateTime()"

    # Allow Alembic to handle all other types normally.
    return False

def run_migrations_offline() -> None:
    context.configure(
       url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
