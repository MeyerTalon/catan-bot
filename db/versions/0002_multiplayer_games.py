"""multiplayer games: games and game_players replace game_sessions.

game_sessions held one opaque state blob per user and nothing wrote to it
beyond the old scaffolding endpoints, so it is dropped rather than migrated.

Revision ID: 0002_multiplayer_games
Revises: 0001_initial_schema
Create Date: 2026-09-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0002_multiplayer_games'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """add users.username, create games and game_players, drop game_sessions."""
    op.add_column('users', sa.Column('username', sa.String(length=64), nullable=True))

    op.create_table(
        'games',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('host_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('max_players', sa.Integer(), nullable=False),
        sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_games_host_user_id'), 'games', ['host_user_id'], unique=False)
    op.create_index(op.f('ix_games_status'), 'games', ['status'], unique=False)

    op.create_table(
        'game_players',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('seat', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'seat', name='uq_game_players_game_seat'),
        sa.UniqueConstraint('game_id', 'user_id', name='uq_game_players_game_user'),
    )
    op.create_index(op.f('ix_game_players_game_id'), 'game_players', ['game_id'], unique=False)
    op.create_index(op.f('ix_game_players_user_id'), 'game_players', ['user_id'], unique=False)

    op.drop_index(op.f('ix_game_sessions_user_id'), table_name='game_sessions')
    op.drop_table('game_sessions')


def downgrade() -> None:
    """restore game_sessions (empty), drop the multiplayer tables and users.username."""
    op.create_table(
        'game_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_game_sessions_user_id'), 'game_sessions', ['user_id'], unique=False)

    op.drop_index(op.f('ix_game_players_user_id'), table_name='game_players')
    op.drop_index(op.f('ix_game_players_game_id'), table_name='game_players')
    op.drop_table('game_players')
    op.drop_index(op.f('ix_games_status'), table_name='games')
    op.drop_index(op.f('ix_games_host_user_id'), table_name='games')
    op.drop_table('games')
    op.drop_column('users', 'username')
