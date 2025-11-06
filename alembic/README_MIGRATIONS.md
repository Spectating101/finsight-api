# Database Migrations with Alembic

This directory contains database migration scripts managed by Alembic.

## Setup

Alembic is already configured to read from `DATABASE_URL` environment variable.

## Common Commands

### Create a new migration
```bash
# After making changes to database schema
alembic revision -m "description of changes"
```

### Apply migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>
```

### Check current version
```bash
alembic current
```

### View migration history
```bash
alembic history
```

### View pending migrations
```bash
alembic show head
```

## Creating the Initial Migration

The initial database schema is defined in `config/database_schema.sql`. To create the baseline migration:

```bash
# This has already been done, but for reference:
alembic revision -m "Initial schema"
# Then manually copy SQL from database_schema.sql into the migration file
```

## Important Notes

1. **Always test migrations on staging first**
2. **Backup database before running migrations in production**
3. **Migrations should be reversible** (implement both `upgrade()` and `downgrade()`)
4. **Never edit applied migrations** - create a new one instead
5. **Commit migrations to version control**

## Production Deployment

```bash
# Set environment variable
export DATABASE_URL="postgresql://user:pass@host/dbname"

# Run migrations
alembic upgrade head
```

## Rollback

If something goes wrong:

```bash
# Rollback last migration
alembic downgrade -1

# Or rollback to specific version
alembic downgrade <revision_id>
```

## Heroku Deployment

Migrations can be run as a release phase in your `Procfile`:

```
release: alembic upgrade head
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

Or manually after deployment:

```bash
heroku run alembic upgrade head --app your-app-name
```
