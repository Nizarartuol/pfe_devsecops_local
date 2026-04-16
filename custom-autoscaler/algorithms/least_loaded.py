"""
ALGORITHME 2 — LEAST LOADED FIRST (LLF)
========================================
Principe : Identifie les services les plus chargés et
les services les moins chargés. Si un service est très
chargé, il reçoit une ressource supplémentaire en priorité.

Différence avec threshold :
- Threshold regarde chaque service indépendamment
- LLF compare les services entre eux et priorise
  les ressources vers les plus sollicités

Stratégie : classement des services par charge CPU,
le plus chargé reçoit le scaling en premier.
"""

import subprocess
import time
import logging

# 🔥 IMPORT NORMALIZER
from metrics.metrics_normalizer import get_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [LEAST_LOADED] %(message)s')

NAMESPACE = "dev"
HIGH_LOAD_THRESHOLD = 0.65
LOW_LOAD_THRESHOLD = 0.25
MIN_REPLICAS = 1
MAX_REPLICAS = 5
COOLDOWN_SECONDS = 45
INTERVAL_SECONDS = 15
MAX_SCALE_PER_CYCLE = 2

SERVICES = [
    "frontend", "adservice", "cartservice", "checkoutservice",
    "currencyservice", "emailservice", "paymentservice",
    "productcatalogservice", "recommendationservice", "shippingservice"
]


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


def least_loaded_decision(cpu_usage_map):
    decisions = {}
    
    sorted_by_load = sorted(cpu_usage_map.items(),
                            key=lambda x: x[1], reverse=True)
    
    for rank, (service, cpu) in enumerate(sorted_by_load):
        replicas = get_current_replicas(service)
        
        if cpu > HIGH_LOAD_THRESHOLD and replicas < MAX_REPLICAS:
            decisions[service] = {
                "action": "SCALE_UP",
                "target": replicas + 1,
                "cpu": cpu,
                "rank": rank,
                "priority": cpu
            }
        elif cpu < LOW_LOAD_THRESHOLD and replicas > MIN_REPLICAS:
            decisions[service] = {
                "action": "SCALE_DOWN",
                "target": replicas - 1,
                "cpu": cpu,
                "rank": rank,
                "priority": -cpu
            }
        else:
            decisions[service] = {
                "action": "MAINTAIN",
                "target": replicas,
                "cpu": cpu,
                "rank": rank
            }
    
    return decisions


def run():
    logging.info("🚀 Démarrage Least Loaded First Autoscaler")
    
    last_scale_time = {}
    
    while True:
        # 🔥 CPU NORMALISÉ
        metrics = get_metrics()
        cpu_map = metrics["cpu"]
        
        # Affichage classement
        sorted_services = sorted(cpu_map.items(), key=lambda x: x[1], reverse=True)
        logging.info("📊 Classement par charge (décroissant):")
        for i, (svc, cpu) in enumerate(sorted_services):
            logging.info(f"  {i+1}. {svc}: {cpu:.2%}")
        
        # Décisions
        decisions = least_loaded_decision(cpu_map)
        
        scale_up_candidates = [
            (s, d) for s, d in decisions.items() if d["action"] == "SCALE_UP"
        ]
        scale_up_candidates.sort(key=lambda x: x[1]["priority"], reverse=True)
        
        scaled_count = 0
        now = time.time()
        
        for service, decision in scale_up_candidates:
            if scaled_count >= MAX_SCALE_PER_CYCLE:
                break
            last_scale = last_scale_time.get(service, 0)
            if (now - last_scale) > COOLDOWN_SECONDS:
                scale_deployment(service, decision["target"])
                last_scale_time[service] = now
                scaled_count += 1
        
        # Scale down
        for service, decision in decisions.items():
            if decision["action"] == "SCALE_DOWN":
                last_scale = last_scale_time.get(service, 0)
                if (now - last_scale) > COOLDOWN_SECONDS * 2:
                    scale_deployment(service, decision["target"])
                    last_scale_time[service] = now
        
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run()