#!/bin/bash
# Script d'analyse automatique des résultats kube-bench
# Usage: ./analyze-results.sh

set -euo pipefail

NAMESPACE="security"
JOB_NAME="kube-bench"
OUTPUT_FILE="kube-bench-report-$(date +%Y%m%d-%H%M%S).json"

echo "=========================================="
echo "  KUBE-BENCH CIS KUBERNETES BENCHMARK"
echo "  Date    : $(date)"
echo "  Cluster : $(kubectl config current-context)"
echo "=========================================="

# Attendre que le job soit terminé
echo "[*] Attente de la fin du job kube-bench..."
kubectl wait --for=condition=complete job/$JOB_NAME -n $NAMESPACE --timeout=300s

# Récupérer le pod
POD=$(kubectl get pods -n $NAMESPACE -l job-name=$JOB_NAME \
  -o jsonpath='{.items[0].metadata.name}')

echo "[*] Pod kube-bench : $POD"

# Extraire les logs JSON
echo "[*] Extraction des résultats..."
kubectl logs $POD -n $NAMESPACE > /tmp/$OUTPUT_FILE

# Analyser avec Python
python3 << EOF
import json, sys

with open('/tmp/$OUTPUT_FILE') as f:
    try:
        data = json.load(f)
    except:
        print("[ERREUR] Output non-JSON, affichage brut :")
        f.seek(0)
        print(f.read())
        sys.exit(1)

totals = {"PASS": 0, "FAIL": 0, "WARN": 0, "INFO": 0}
critical_fails = []
warn_items = []

for control in data.get("Controls", []):
    section = control.get("text", "Unknown")
    for test in control.get("tests", []):
        for result in test.get("results", []):
            status = result.get("status", "INFO")
            totals[status] = totals.get(status, 0) + 1
            if status == "FAIL":
                critical_fails.append({
                    "id": result.get("test_number", "N/A"),
                    "section": section,
                    "desc": result.get("test_desc", ""),
                    "remediation": result.get("remediation", "")
                })
            elif status == "WARN":
                warn_items.append({
                    "id": result.get("test_number", "N/A"),
                    "desc": result.get("test_desc", "")
                })

print(f"\n{'='*50}")
print(f"  RÉSUMÉ CIS BENCHMARK")
print(f"{'='*50}")
print(f"  ✅ PASS  : {totals['PASS']}")
print(f"  ❌ FAIL  : {totals['FAIL']}")
print(f"  ⚠️  WARN  : {totals['WARN']}")
print(f"  ℹ️  INFO  : {totals['INFO']}")
print(f"{'='*50}")

if critical_fails:
    print(f"\n[CRITICAL FAILURES — {len(critical_fails)} trouvés]")
    for i, f in enumerate(critical_fails, 1):
        print(f"\n  [{i}] {f['id']} — Section: {f['section']}")
        print(f"      Problème    : {f['desc']}")
        print(f"      Remédiation : {f['remediation'][:150]}...")

if warn_items:
    print(f"\n[WARNINGS — {len(warn_items)} trouvés]")
    for w in warn_items[:5]:
        print(f"  [{w['id']}] {w['desc']}")

print(f"\n[*] Rapport complet sauvegardé : /tmp/$OUTPUT_FILE")
EOF

echo ""
echo "[✓] Analyse terminée."
