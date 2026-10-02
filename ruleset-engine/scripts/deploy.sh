#!/bin/bash
set -e

echo "🚀 Deploying Pompom Ruleset Engine..."

# Check prerequisites
command -v java >/dev/null 2>&1 || { echo "❌ Java not found. Install Java 21+"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found. Install Docker"; exit 1; }

# Check .env file
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copy .env.example and configure."
    exit 1
fi

# Start PostgreSQL
echo "📦 Starting PostgreSQL..."
docker-compose up postgres -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
sleep 5

# Run migrations
echo "🗄️  Running database migrations..."
./mvnw liquibase:update

# Build application
echo "🔨 Building application..."
./mvnw clean package -DskipTests

# Run tests
echo "🧪 Running tests..."
./mvnw test

# Start application
echo "✅ Starting Ruleset Engine..."
./mvnw spring-boot:run &

# Wait for application to start
echo "⏳ Waiting for application..."
sleep 10

# Health check
echo "🏥 Health check..."
curl -f http://localhost:8081/actuator/health || { echo "❌ Health check failed"; exit 1; }

echo "✅ Deployment complete!"
echo "🌐 API available at: http://localhost:8081"
echo "📊 Health: http://localhost:8081/actuator/health"
echo "📚 Docs: ./docs/"
