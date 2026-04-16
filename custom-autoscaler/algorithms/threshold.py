"""
ALGORITHME 1 — THRESHOLD BASED SCALING (NORMALISÉ)
===================================================
Principe :
- Utilise des métriques normalisées (% CPU)
- Compare à des seuils fixes
- Décide scale up / scale down
- Exécute via Kubernetes API (kubectl)

Version propre pour comparaison scientifique
avec HPA / VPA / autres algorithmes
"""

import subprocess
import time
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics.metrics_normalizer import get_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [THRESHOLD] %(message)s')


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
NAMESPACE = "dev"

SCALE_UP_THRESHOLD = 70      # %
SCALE_DOWN_THRESHOLD = 30    # %

MIN_REPLICAS = 1
MAX_REPLICAS = 5

COOLDOWN_SECONDS = 60
INTERVAL_SECONDS = 15


SERVICES = [
    "frontend",
    "adservice",
    "cartservice",
    "checkoutservice",
    "currencyservice",
    "emailservice",
    "paymentservice",
    "productcatalogservice",
    "recommendationservice",
    "shippingservice"
]


# ─────────────────────────────────────────────
# KUBERNETES FUNCTIONS
# ─────────────────────────────────────────────
def get_current_replicas(service):
    result = subprocess.run(
        [
            "kubectl", "get", "deployment", service,
            "-n", NAMESPACE,
            "-o", "jsonpath={.spec.replicas}"
        ],
        capture_output=True,
        text=True
    )

    try:
        return int(result.stdout.strip())
    except:
        return 1


def scale_deployment(service, replicas):
    result = subprocess.run(
        [
            "kubectl", "scale", "deployment", service,
            "-n", NAMESPACE,
            f"--replicas={replicas}"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        logging.info(f"✅ {service} scaled → {replicas} replicas")
    else:
        logging.error(f"❌ Scaling error {service}: {result.stderr}")


# ─────────────────────────────────────────────
# DECISION ENGINE
# ─────────────────────────────────────────────
def threshold_decision(cpu_percent, replicas):
    """
    Logique simple et claire :

    - CPU > 70% → scale up
    - CPU < 30% → scale down
    - sinon → stable
    """

    if cpu_percent > SCALE_UP_THRESHOLD and replicas < MAX_REPLICAS:
        return replicas + 1, "SCALE_UP"

    elif cpu_percent < SCALE_DOWN_THRESHOLD and replicas > MIN_REPLICAS:
        return replicas - 1, "SCALE_DOWN"

    else:
        return replicas, "MAINTAIN"


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def run():
    logging.info("🚀 Threshold Autoscaler (NORMALIZED) started")
    logging.info(f"UP={SCALE_UP_THRESHOLD}% DOWN={SCALE_DOWN_THRESHOLD}%")

    last_scale_time = {}

    while True:
        for service in SERVICES:

            # ── METRICS NORMALISÉES ──
            metrics = get_metrics(service)
            cpu = metrics["cpu_percent"]

            replicas = get_current_replicas(service)
            new_replicas, action = threshold_decision(cpu, replicas)

            now = time.time()
            last_scale = last_scale_time.get(service, 0)

            # ── COOLDOWN LOGIC ──
            if action != "MAINTAIN" and (now - last_scale) > COOLDOWN_SECONDS:

                scale_deployment(service, new_replicas)
                last_scale_time[service] = now

                logging.info(
                    f"📊 {service} | CPU={cpu:.2f}% | "
                    f"{replicas} → {new_replicas} | {action}"
                )

            else:
                logging.info(
                    f"📊 {service} | CPU={cpu:.2f}% | replicas={replicas} | {action}"
                )

        time.sleep(INTERVAL_SECONDS)


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    run()