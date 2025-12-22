#!/bin/bash

echo "🌱 Seeding Chronicle D1 Database (Remote)..."

# Reset Database (Delete all rows)
echo "🧹 Cleaning up old data..."
npx wrangler d1 execute chronicle-db --command "DELETE FROM drops;" --remote

# Seed Data
echo "💾 Inserting seed data..."
npx wrangler d1 execute chronicle-db --file=apps/chronicle-server/data/seed_d1.sql --remote

echo "✅ Seed Complete!"
