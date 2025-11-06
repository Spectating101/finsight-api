#!/bin/bash
# FinSight API - One-Click Deployment Script
# This script handles complete deployment to Railway/Render/Heroku

set -e  # Exit on error

echo "🚀 FinSight API - Automated Deployment"
echo "======================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { echo -e "${RED}❌ Python 3 required but not installed${NC}"; exit 1; }
command -v git >/dev/null 2>&1 || { echo -e "${RED}❌ Git required but not installed${NC}"; exit 1; }

echo -e "${GREEN}✓ Prerequisites met${NC}"

# Deployment platform selection
echo ""
echo "Select deployment platform:"
echo "1) Railway (Recommended - easiest)"
echo "2) Render (Good free tier)"
echo "3) Heroku (Classic choice)"
echo "4) Docker (Self-hosted)"
read -p "Enter choice [1-4]: " platform

case $platform in
    1)
        PLATFORM="railway"
        ;;
    2)
        PLATFORM="render"
        ;;
    3)
        PLATFORM="heroku"
        ;;
    4)
        PLATFORM="docker"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}Selected: $PLATFORM${NC}"

# Environment variables
echo ""
echo "📝 Setting up environment variables..."

# Check if .env exists, create if not
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || touch .env
fi

# Required environment variables
read -p "Database URL (PostgreSQL): " DATABASE_URL
read -p "Redis URL: " REDIS_URL
read -p "Stripe Secret Key: " STRIPE_SECRET_KEY
read -p "Stripe Webhook Secret: " STRIPE_WEBHOOK_SECRET
read -p "Sentry DSN (optional, press enter to skip): " SENTRY_DSN
read -p "Custom Domain (optional, press enter to skip): " CUSTOM_DOMAIN

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

# Write to .env
cat > .env << EOF
# Database
DATABASE_URL=$DATABASE_URL

# Redis
REDIS_URL=$REDIS_URL
REDIS_TLS=true

# Stripe
STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET

# Security
SECRET_KEY=$SECRET_KEY

# Environment
ENVIRONMENT=production

# Sentry (optional)
${SENTRY_DSN:+SENTRY_DSN=$SENTRY_DSN}

# CORS
${CUSTOM_DOMAIN:+ALLOWED_ORIGINS=https://$CUSTOM_DOMAIN,https://www.$CUSTOM_DOMAIN}
EOF

echo -e "${GREEN}✓ Environment variables configured${NC}"

# Platform-specific deployment
echo ""
echo "🚢 Deploying to $PLATFORM..."

case $PLATFORM in
    "railway")
        echo ""
        echo "Railway deployment steps:"
        echo "1. Install Railway CLI: npm i -g @railway/cli"
        echo "2. Login: railway login"
        echo "3. Create project: railway init"
        echo "4. Add PostgreSQL: railway add"
        echo "5. Add Redis: railway add"
        echo "6. Deploy: railway up"
        echo ""
        echo "Setting up Railway configuration..."

        # Create railway.json
        cat > railway.json << 'EOF'
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
EOF
        echo -e "${GREEN}✓ Railway configuration created${NC}"
        echo -e "${YELLOW}Run: railway up${NC}"
        ;;

    "render")
        echo ""
        echo "Creating render.yaml configuration..."

        cat > render.yaml << 'EOF'
services:
  - type: web
    name: finsight-api
    env: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
      - key: STRIPE_SECRET_KEY
        sync: false
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
      - key: SECRET_KEY
        sync: false
      - key: ENVIRONMENT
        value: production
      - key: REDIS_TLS
        value: true

databases:
  - name: finsight-db
    databaseName: finsight
    user: finsight
    plan: free

  - name: finsight-redis
    plan: free
EOF
        echo -e "${GREEN}✓ Render configuration created${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Go to https://dashboard.render.com"
        echo "2. Click 'New' → 'Blueprint'"
        echo "3. Connect your GitHub repo"
        echo "4. Add environment variables in dashboard"
        ;;

    "heroku")
        echo ""
        echo "Heroku deployment..."

        # Check if Heroku CLI installed
        if ! command -v heroku &> /dev/null; then
            echo -e "${YELLOW}Installing Heroku CLI...${NC}"
            curl https://cli-assets.heroku.com/install.sh | sh
        fi

        # Create Procfile
        cat > Procfile << 'EOF'
web: alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port $PORT
EOF

        # Create runtime.txt
        echo "python-3.11.6" > runtime.txt

        read -p "Heroku app name: " APP_NAME

        echo "Creating Heroku app..."
        heroku create $APP_NAME

        echo "Adding PostgreSQL..."
        heroku addons:create heroku-postgresql:mini

        echo "Adding Redis..."
        heroku addons:create heroku-redis:mini

        echo "Setting environment variables..."
        heroku config:set STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY"
        heroku config:set STRIPE_WEBHOOK_SECRET="$STRIPE_WEBHOOK_SECRET"
        heroku config:set SECRET_KEY="$SECRET_KEY"
        heroku config:set ENVIRONMENT=production
        heroku config:set REDIS_TLS=true

        echo "Deploying..."
        git push heroku main

        echo -e "${GREEN}✓ Deployed to Heroku${NC}"
        echo "App URL: https://$APP_NAME.herokuapp.com"
        ;;

    "docker")
        echo ""
        echo "Creating Docker configuration..."

        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start server
CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000
EOF

        cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/finsight
      - REDIS_URL=redis://redis:6379
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=finsight
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
EOF

        echo -e "${GREEN}✓ Docker configuration created${NC}"
        echo ""
        echo "To deploy:"
        echo "  docker-compose up -d"
        ;;
esac

# Database migration
echo ""
echo "📊 Database setup..."
echo "After deployment, run database migrations:"
echo "  alembic upgrade head"

# Post-deployment checklist
echo ""
echo "✅ Deployment Configuration Complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 POST-DEPLOYMENT CHECKLIST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. ✓ Platform configuration created"
echo "2. ⏳ Deploy application to $PLATFORM"
echo "3. ⏳ Run database migrations: alembic upgrade head"
echo "4. ⏳ Test health endpoint: curl YOUR_URL/health"
echo "5. ⏳ Create Stripe products (see stripe_products.json)"
echo "6. ⏳ Set up custom domain (optional)"
echo "7. ⏳ Configure DNS records"
echo "8. ⏳ Set up monitoring (UptimeRobot)"
echo "9. ⏳ Test complete signup flow"
echo "10. ⏳ Post launch announcements (see LAUNCH_POSTS.md)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Documentation:"
echo "  - Stripe setup: See stripe_products.json"
echo "  - Launch posts: See LAUNCH_POSTS.md"
echo "  - Monitoring: See MONITORING_SETUP.md"
echo ""
echo -e "${GREEN}Good luck with your launch! 🚀${NC}"
