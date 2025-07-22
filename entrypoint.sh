#!/bin/bash
set -e

echo "🚀 Starting Healthcare Cost Navigator deployment..."

# Run Alembic migrations
echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Database migrations completed!"

# Run ETL process
echo "📊 Running ETL process..."
python etl.py
echo "✅ ETL process completed!"

# Start the main application
echo "🌟 Starting the API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
