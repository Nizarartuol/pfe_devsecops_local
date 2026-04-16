"""
ALGORITHME 4 — PREDICTIVE SCALING
====================================
Principe : Au lieu de réagir quand la charge arrive,
on prédit la charge future et on scale AVANT.

Méthode utilisée : Régression linéaire simple sur
l'historique des 10 dernières mesures → prédit la
charge dans les 2 prochaines minutes.

Avantage vs threshold :
- Threshold réagit APRÈS → latence pendant le scaling
- Predictive scale AVANT → pas de dégradation de perf

Limitation : précision dépend de la régularité du trafic
"""

import subprocess
import time
import logging
import numpy as np
from collections import defaultdict, deque

# ✅ IMPORT NORMALIZER
from metrics.metrics_normalizer import get_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [PREDICTIVE] %(message)s')

NAMESPACE = "dev"
HISTORY_SIZE = 10
PREDICTION_STEPS = 4
SCALE_UP_THRESHOLD = 0.60
SCALE_DOWN_THRESHOLD = 0.25
MIN_REPLICAS = 1
MAX_REPLICAS = 5
INTERVAL_SECONDS = 15

SERVICES = [
    "frontend", "adservice", "cartservice", "checkoutservice",
    "currencyservice", "emailservice", "paymentservice",
    "productcatalogservice", "recommendationservice", "shippingservice"
]

cpu_history = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))


# ❌ SUPPRIMÉ : get_cpu_usage()


def get_current_replicas(service):
    result = subprocess.run(
        ["kubectl", "get", "deployment", service, "-n", NAMESPACE,
         "-o", "jsonpath={.spec.replicas}"],
        capture_output=True, text=True
    )
    try:
        return int(result.stdout.strip())
    except:
        return 1


def scale_deployment(service, replicas):
    result = subprocess.run(
        ["kubectl", "scale", "deployment", service,
         "-n", NAMESPACE, f"--replicas={replicas}"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        logging.info(f"✅ {service} → {replicas} replicas")


def predict_cpu(history):
    if len(history) < 3:
        return list(history)[-1] if history else 0.0

    x = np.arange(len(history))
    y = np.array(list(history))

    coeffs = np.polyfit(x, y, 1)
    future_x = len(history) + PREDICTION_STEPS
    predicted = np.polyval(coeffs, future_x)

    return max(0.0, min(1.0, predicted))


def predictive_decision(service, current_cpu, current_replicas):
    predicted_cpu = predict_cpu(cpu_history[service])

    logging.info(f"{service}: CPU actuel={current_cpu:.2%} | "
                 f"CPU prédit ({PREDICTION_STEPS*15}s)={predicted_cpu:.2%}")

    if predicted_cpu > SCALE_UP_THRESHOLD and current_replicas < MAX_REPLICAS:
        return current_replicas + 1, "SCALE_UP (prédictif)", predicted_cpu
    elif predicted_cpu < SCALE_DOWN_THRESHOLD and current_replicas > MIN_REPLICAS:
        return current_replicas - 1, "SCALE_DOWN (prédictif)", predicted_cpu
    else:
        return current_replicas, "MAINTAIN", predicted_cpu


def run():
    logging.info("🚀 Démarrage Predictive Autoscaler")
    logging.info(f"Prédiction: {PREDICTION_STEPS * INTERVAL_SECONDS}s en avance")

    last_scale_time = {}

    while True:
        # ✅ récupérer toutes les métriques en une fois
        metrics = get_metrics()

        for service in SERVICES:
            cpu = metrics.get(service, {}).get("cpu_percent", 0.0)

            cpu_history[service].append(cpu)

            replicas = get_current_replicas(service)

            new_replicas, action, predicted = predictive_decision(
                service, cpu, replicas
            )

            now = time.time()
            last_scale = last_scale_time.get(service, 0)

            if action != "MAINTAIN" and (now - last_scale) > 30:
                scale_deployment(service, new_replicas)
                last_scale_time[service] = now

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run()