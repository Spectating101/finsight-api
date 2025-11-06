"""Initial schema from database_schema.sql

Revision ID: d3fed0c766be
Revises:
Create Date: 2025-11-06 10:20:44.029468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3fed0c766be'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all tables, indexes, functions, and triggers."""

    # Create users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(64) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            email_verified BOOLEAN DEFAULT false,
            password_hash VARCHAR(255),

            company_name VARCHAR(255),
            website VARCHAR(255),

            tier VARCHAR(20) DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'professional', 'enterprise')),
            status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'cancelled', 'trial')),

            api_calls_this_month INTEGER DEFAULT 0,
            api_calls_limit INTEGER DEFAULT 100,
            last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            stripe_customer_id VARCHAR(255) UNIQUE,
            stripe_subscription_id VARCHAR(255),
            billing_period_start TIMESTAMP,
            billing_period_end TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_api_call TIMESTAMP,
            last_login TIMESTAMP
        )
    """)

    # Create api_keys table
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id VARCHAR(64) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

            key_hash VARCHAR(255) UNIQUE NOT NULL,
            key_prefix VARCHAR(20) NOT NULL,
            name VARCHAR(100) DEFAULT 'Default Key',

            is_active BOOLEAN DEFAULT true,
            is_test_mode BOOLEAN DEFAULT false,

            total_calls BIGINT DEFAULT 0,
            calls_this_month INTEGER DEFAULT 0,
            last_used_at TIMESTAMP,

            allowed_ips TEXT[],
            allowed_domains TEXT[],

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)

    # Create usage_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_records (
            record_id VARCHAR(64) PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            key_id VARCHAR(64) NOT NULL REFERENCES api_keys(key_id) ON DELETE CASCADE,

            endpoint VARCHAR(255) NOT NULL,
            method VARCHAR(10) NOT NULL,
            status_code INTEGER NOT NULL,

            credits_used INTEGER DEFAULT 1,
            response_time_ms INTEGER,

            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address INET,
            user_agent TEXT
        )
    """)

    # Create subscription_history table
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscription_history (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

            old_tier VARCHAR(20),
            new_tier VARCHAR(20) NOT NULL,
            event_type VARCHAR(50),

            stripe_subscription_id VARCHAR(255),
            stripe_event_id VARCHAR(255),

            change_reason VARCHAR(50),
            metadata JSONB,

            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create webhook_events table
    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_events (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(255) UNIQUE NOT NULL,
            event_type VARCHAR(100) NOT NULL,

            payload JSONB NOT NULL,
            processed BOOLEAN DEFAULT false,
            processing_error TEXT,

            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        )
    """)

    # Create feature_flags table
    op.execute("""
        CREATE TABLE IF NOT EXISTS feature_flags (
            feature_name VARCHAR(100) PRIMARY KEY,
            description TEXT,

            free_tier BOOLEAN DEFAULT false,
            starter_tier BOOLEAN DEFAULT false,
            professional_tier BOOLEAN DEFAULT true,
            enterprise_tier BOOLEAN DEFAULT true,

            enabled BOOLEAN DEFAULT true,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes on users table
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_stripe_customer', 'users', ['stripe_customer_id'])
    op.create_index('idx_users_tier', 'users', ['tier'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_tier_status', 'users', ['tier', 'status'])

    # Create indexes on api_keys table
    op.create_index('idx_api_keys_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('idx_api_keys_active', 'api_keys', ['is_active'])
    op.create_index('idx_api_keys_user_active', 'api_keys', ['user_id', 'is_active'])

    # Create indexes on usage_records table
    op.create_index('idx_usage_user_timestamp', 'usage_records', ['user_id', sa.text('timestamp DESC')])
    op.create_index('idx_usage_endpoint', 'usage_records', ['endpoint'])
    op.create_index('idx_usage_timestamp', 'usage_records', [sa.text('timestamp DESC')])
    op.create_index('idx_usage_user_date', 'usage_records', ['user_id', sa.text('timestamp DESC')])

    # Create indexes on subscription_history table
    op.create_index('idx_subscription_user_id', 'subscription_history', ['user_id'])
    op.create_index('idx_subscription_changed_at', 'subscription_history', [sa.text('changed_at DESC')])

    # Create indexes on webhook_events table
    op.create_index('idx_webhook_event_id', 'webhook_events', ['event_id'])
    op.create_index('idx_webhook_event_type', 'webhook_events', ['event_type'])
    op.create_index('idx_webhook_received_at', 'webhook_events', [sa.text('received_at DESC')])

    # Create functions
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION reset_monthly_usage()
        RETURNS INTEGER AS $$
        DECLARE
            rows_updated INTEGER;
        BEGIN
            UPDATE users
            SET api_calls_this_month = 0,
                last_reset_at = CURRENT_TIMESTAMP
            WHERE DATE_TRUNC('month', last_reset_at) < DATE_TRUNC('month', CURRENT_TIMESTAMP);

            GET DIAGNOSTICS rows_updated = ROW_COUNT;

            UPDATE api_keys
            SET calls_this_month = 0
            WHERE DATE_TRUNC('month', COALESCE(last_used_at, created_at)) < DATE_TRUNC('month', CURRENT_TIMESTAMP);

            RETURN rows_updated;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Create triggers
    op.execute("""
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """)

    op.execute("""
        CREATE TRIGGER update_feature_flags_updated_at
            BEFORE UPDATE ON feature_flags
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """)

    # Insert default feature flags
    op.execute("""
        INSERT INTO feature_flags (feature_name, description, free_tier, starter_tier, professional_tier, enterprise_tier) VALUES
            ('sec_edgar_data', 'Access SEC EDGAR filings', true, true, true, true),
            ('yahoo_finance_data', 'Access Yahoo Finance market data', false, true, true, true),
            ('alpha_vantage_data', 'Access Alpha Vantage real-time data', false, false, true, true),
            ('ai_synthesis', 'LLM-powered financial analysis', false, false, true, true),
            ('custom_metrics', 'Create custom calculation formulas', false, false, false, true),
            ('webhooks', 'Webhook notifications for events', false, false, true, true),
            ('priority_support', '24/7 priority support', false, false, false, true),
            ('sla_guarantee', '99.9% uptime SLA', false, false, false, true)
        ON CONFLICT (feature_name) DO NOTHING
    """)


def downgrade() -> None:
    """Downgrade schema - drop everything in reverse order."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_feature_flags_updated_at ON feature_flags")
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS reset_monthly_usage()")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables (in reverse order of dependencies)
    op.execute("DROP TABLE IF EXISTS feature_flags CASCADE")
    op.execute("DROP TABLE IF EXISTS webhook_events CASCADE")
    op.execute("DROP TABLE IF EXISTS subscription_history CASCADE")
    op.execute("DROP TABLE IF EXISTS usage_records CASCADE")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
