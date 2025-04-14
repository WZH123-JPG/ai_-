"""Add chat sessions and messages tables

Revision ID: add_chat_tables
Revises: 62faca85ef56
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import LONGTEXT

# revision identifiers, used by Alembic.
revision = 'add_chat_tables'
down_revision = '62faca85ef56'
branch_labels = None
depends_on = None

def upgrade():
    # 创建chat_sessions表
    op.create_table('chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100, collation='utf8mb4_unicode_ci'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 添加user_id索引
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'])

    # 创建chat_messages表
    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('content', LONGTEXT(charset='utf8mb4', collation='utf8mb4_unicode_ci'), nullable=False),
        sa.Column('is_user', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 添加session_id索引
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])

def downgrade():
    op.drop_index('ix_chat_messages_session_id')
    op.drop_table('chat_messages')
    op.drop_index('ix_chat_sessions_user_id')
    op.drop_table('chat_sessions') 