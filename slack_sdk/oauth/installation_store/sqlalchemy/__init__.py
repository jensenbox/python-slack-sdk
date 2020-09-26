import logging
from logging import Logger
from typing import Optional

from sqlalchemy.engine import Engine
from slack_sdk.oauth.installation_store.installation_store import InstallationStore
from slack_sdk.oauth.installation_store.models.bot import Bot
from slack_sdk.oauth.installation_store.models.installation import Installation

import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, DateTime, Index, and_, desc


class SQLAlchemyInstallationStore(InstallationStore):
    engine: Engine
    client_id: str

    metadata = sqlalchemy.MetaData()
    installations: Table = sqlalchemy.Table(
        "installations",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("client_id", String, nullable=False),
        Column("app_id", String, nullable=False),
        Column("enterprise_id", String),
        Column("team_id", String),
        Column("bot_token", String),
        Column("bot_id", String),
        Column("bot_user_id", String),
        Column("bot_scopes", String),
        Column("user_id", String, nullable=False),
        Column("user_token", String),
        Column("user_scopes", String),
        Column("incoming_webhook_url", String),
        Column("incoming_webhook_channel_id", String),
        Column("incoming_webhook_configuration_url", String),
        Column(
            "installed_at", DateTime, nullable=False, default=sqlalchemy.sql.func.now()
        ),
        Index("installations_idx", "client_id", "enterprise_id", "team_id", "user_id",),
    )

    bots = Table(
        "bots",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("client_id", String, nullable=False),
        Column("app_id", String, nullable=False),
        Column("enterprise_id", String),
        Column("team_id", String),
        Column("bot_token", String),
        Column("bot_id", String),
        Column("bot_user_id", String),
        Column("bot_scopes", String),
        Column(
            "installed_at", DateTime, nullable=False, default=sqlalchemy.sql.func.now()
        ),
        Index("bots_idx", "client_id", "enterprise_id", "team_id",),
    )

    def __init__(
        self,
        client_id: str,
        engine: Engine,
        logger: Logger = logging.getLogger(__name__),
    ):
        self.client_id = client_id
        self._logger = logger
        self.engine = engine

    def create_tables(self):
        self.metadata.create_all(self.engine)

    @property
    def logger(self) -> Logger:
        return self._logger

    def save(self, installation: Installation):
        with self.engine.begin() as conn:
            i = installation.to_dict()
            i["client_id"] = self.client_id
            conn.execute(self.installations.insert(), i)
            b = installation.to_bot().to_dict()
            b["client_id"] = self.client_id
            conn.execute(self.bots.insert(), b)

    def find_bot(
        self, *, enterprise_id: Optional[str], team_id: Optional[str]
    ) -> Optional[Bot]:
        c = self.bots.c
        query = (
            self.bots.select()
            .where(and_(c.enterprise_id == enterprise_id, c.team_id == team_id))
            .order_by(desc(c.installed_at))
            .limit(1)
        )

        with self.engine.connect() as conn:
            result: object = conn.execute(query)
            for row in result:
                return Bot(
                    app_id=row["app_id"],
                    enterprise_id=row["enterprise_id"],
                    team_id=row["team_id"],
                    bot_token=row["bot_token"],
                    bot_id=row["bot_id"],
                    bot_user_id=row["bot_user_id"],
                    bot_scopes=row["bot_scopes"],
                    installed_at=row["installed_at"],
                )
            return None