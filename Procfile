# Heroku Procfile for FinSight API

web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
worker: python -m src.workers.usage_tracker
release: python -m alembic upgrade head
