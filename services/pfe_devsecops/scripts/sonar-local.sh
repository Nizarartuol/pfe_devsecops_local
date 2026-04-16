#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# sonar-local.sh – Run a local SonarQube scan against your self-hosted instance
#
# Prerequisites:
#   1. SonarQube running:  docker run -d -p 9000:9000 sonarqube:community
#   2. sonar-scanner CLI installed and on PATH
#      → Download: https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner/
#   3. Environment variables set:
#        export SONAR_HOST_URL=http://localhost:9000
#        export SONAR_TOKEN=<your-sonarqube-login-token>
#
# Usage (from services/pfe_devsecops/):
#   bash scripts/sonar-local.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Validate environment ──────────────────────────────────────────────────────
: "${SONAR_HOST_URL:?'❌ SONAR_HOST_URL is not set. Export it first: export SONAR_HOST_URL=http://localhost:9000'}"
: "${SONAR_TOKEN:?'❌ SONAR_TOKEN is not set. Export it first: export SONAR_TOKEN=<your-token>'}"

# ── Run sonar-scanner ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"   # services/pfe_devsecops/

echo "▶ Running SonarQube local scan"
echo "   Project dir : $PROJECT_DIR"
echo "   SonarQube   : $SONAR_HOST_URL"
echo ""

sonar-scanner \
  -Dsonar.host.url="$SONAR_HOST_URL" \
  -Dsonar.login="$SONAR_TOKEN" \
  -Dproject.settings="$PROJECT_DIR/sonar-project.properties" \
  -Dsonar.projectBaseDir="$PROJECT_DIR"

echo ""
echo "✅ Scan complete. Open $SONAR_HOST_URL/dashboard?id=Nizarartuol_pfe_devsecops to view results."
