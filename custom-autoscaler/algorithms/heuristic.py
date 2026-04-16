"""
ALGORITHME 7 — HEURISTIC HYBRID
=================================
Principe : Combine plusieurs stratégies heuristiques
pour prendre la meilleure décision selon le contexte.

Heuristiques utilisées :
1. Urgence (CPU très élevé → scale up immédiat)
2. Tendance (CPU monte → scale up préventif)
3. Stabilité (oscillations → ne pas scaler)
4. Économie (CPU bas depuis longtemps → scale down)
5. Priorité service (frontend > autres services)

L'algorithme choisit l'heuristique appropriée selon
l'état actuel du service → "intelligence" contextuelle.

C'est une approche "règles expertes" qui encode
la connaissance humaine en règles automatiques.
"""

import subprocess
import time
import logging
import numpy as np
from collections import defaultdict, deque

# 🔥 IMPORT NORMALIZER
from metrics.metrics_normalizer import get_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [HEURISTIC] %(message)s')

NAMESPACE = "dev"
HISTORY_SIZE = 8
INTERVAL_SECONDS = 15
MIN_REPLICAS = 1
MAX_REPLICAS = 5

SERVICE_PRIORITY = {
    "frontend": 1,
    "cartservice": 1,
    "checkoutservice": 1,
    "paymentservice": 2,
    "productcatalogservice": 2,
    "adservice": 3,
    "currencyservice": 3,
    "emailservice": 3,
    "recommendationservice": 3,
    "shippingservice": 3,
}

SERVICES = list(SERVICE_PRIORITY.keys())

cpu_history = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))
scale_history = defaultdict(list)


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


def scale_deployment(service, replicas, reason):
    result = subprocess.run(
        ["kubectl", "scale", "deployment", service,
         "-n", NAMESPACE, f"--replicas={replicas}"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        logging.info(f"✅ {service} → {replicas} replicas [Raison: {reason}]")
        scale_history[service].append({
            "time": time.time(),
            "replicas": replicas,
            "reason": reason
        })


def detect_oscillation(service):
    recent = scale_history[service][-4:] if len(scale_history[service]) >= 4 else []
    if len(recent) < 4:
        return False
    
    directions = []
    for i in range(1, len(recent)):
        if recent[i]["replicas"] > recent[i-1]["replicas"]:
            directions.append("up")
        elif recent[i]["replicas"] < recent[i-1]["replicas"]:
            directions.append("down")
    
    return "up" in directions and "down" in directions


def get_trend(history):
    if len(history) < 3:
        return "stable"
    
    values = list(history)
    recent_avg = np.mean(values[-3:])
    old_avg = np.mean(values[:3])
    
    diff = recent_avg - old_avg
    
    if diff > 0.05:
        return "rising"
    elif diff < -0.05:
        return "falling"
    else:
        return "stable"


def heuristic_decision(service, cpu, replicas):
    priority = SERVICE_PRIORITY.get(service, 3)
    trend = get_trend(cpu_history[service])
    oscillating = detect_oscillation(service)
    
    if cpu > 0.85 and replicas < MAX_REPLICAS:
        return replicas + 1, "URGENCE_CRITIQUE"
    
    if oscillating:
        return replicas, "STABILITE_ANTI_OSCILLATION"
    
    if priority == 1:
        if cpu > 0.60 and replicas < MAX_REPLICAS:
            return replicas + 1, "SCALE_UP_CRITIQUE"
        elif cpu < 0.20 and replicas > MIN_REPLICAS:
            return replicas - 1, "SCALE_DOWN_CRITIQUE"
    
    if trend == "rising" and cpu > 0.50 and replicas < MAX_REPLICAS:
        return replicas + 1, "SCALE_UP_PREDICTIF_TENDANCE"
    
    if trend == "falling" and cpu < 0.25 and replicas > MIN_REPLICAS:
        return replicas - 1, "SCALE_DOWN_ECONOMIQUE"
    
    if priority >= 2:
        if cpu > 0.70 and replicas < MAX_REPLICAS:
            return replicas + 1, "SCALE_UP_STANDARD"
        elif cpu < 0.15 and replicas > MIN_REPLICAS:
            return replicas - 1, "SCALE_DOWN_STANDARD"
    
    return replicas, f"MAINTIEN (CPU={cpu:.1%}, trend={trend})"


def run():
    logging.info("🚀 Démarrage Heuristic Hybrid Autoscaler")

    last_scale_time = defaultdict(int)
    cooldown = {1: 20, 2: 40, 3: 60}
    
    while True:
        # 🔥 RÉCUPÉRATION CENTRALISÉE
        metrics = get_metrics()
        cpu_map = metrics["cpu"]

        for service in SERVICES:
            cpu = cpu_map[service]
            cpu_history[service].append(cpu)

            replicas = get_current_replicas(service)
            new_replicas, heuristic = heuristic_decision(service, cpu, replicas)
            
            priority = SERVICE_PRIORITY.get(service, 3)
            svc_cooldown = cooldown[priority]
            now = time.time()
            
            if (new_replicas != replicas and
                    (now - last_scale_time[service]) > svc_cooldown):
                scale_deployment(service, new_replicas, heuristic)
                last_scale_time[service] = now
            else:
                trend = get_trend(cpu_history[service])
                logging.info(f"📊 {service}(P{priority}): CPU={cpu:.1%} "
                             f"trend={trend} replicas={replicas} → {heuristic}")
        
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run()