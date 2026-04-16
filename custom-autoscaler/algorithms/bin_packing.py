"""
ALGORITHME 3 — BIN PACKING (FF / FFD / BF / BFD)
==================================================
Principe inspiré du problème classique bin packing :
"Comment remplir des boîtes de capacité fixe avec
des objets de tailles variables de façon optimale ?"

Adapté à Kubernetes :
- Boîtes = nodes (capacité CPU/RAM fixe)
- Objets = pods (consomment CPU/RAM)

Stratégies disponibles :
- FF  (First Fit)            : premier node avec espace
- FFD (First Fit Decreasing) : trier pods par taille d'abord
- BF  (Best Fit)             : node avec moins d'espace restant
- BFD (Best Fit Decreasing)  : BF + tri décroissant

Objectif : minimiser les nodes utilisés → économie de ressources
"""

import subprocess
import time
import logging

# ✅ NOUVEAU : import centralisé
from metrics.metrics_normalizer import get_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BIN_PACKING] %(message)s')

NAMESPACE = "dev"
NODE_CAPACITY = 1.0  # capacité normalisée d'un node (100% CPU)
POD_CPU_COST = 0.1   # chaque pod coûte ~10% de CPU
MIN_REPLICAS = 1
MAX_REPLICAS = 5
INTERVAL_SECONDS = 20

SERVICES = [
    "frontend", "adservice", "cartservice", "checkoutservice",
    "currencyservice", "emailservice", "paymentservice",
    "productcatalogservice", "recommendationservice", "shippingservice"
]


def get_service_cpu(service):
    """CPU usage normalisé entre 0 et 1 via metrics_normalizer."""
    try:
        metrics = get_metrics(service)
        cpu_percent = metrics["cpu_percent"]  # ex: 82%
        return min(cpu_percent / 100.0, 1.0)  # convert → [0,1]
    except:
        return 0.0


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


def first_fit(items, bin_capacity):
    """FF : place chaque item dans le premier bin avec assez d'espace."""
    bins = []
    for item_size in items:
        placed = False
        for b in bins:
            if b["remaining"] >= item_size:
                b["items"].append(item_size)
                b["remaining"] -= item_size
                placed = True
                break
        if not placed:
            bins.append({"items": [item_size], "remaining": bin_capacity - item_size})
    return bins


def best_fit(items, bin_capacity):
    """BF : place chaque item dans le bin avec le moins d'espace restant."""
    bins = []
    for item_size in items:
        best_bin = None
        best_remaining = float('inf')
        for b in bins:
            if b["remaining"] >= item_size and b["remaining"] < best_remaining:
                best_bin = b
                best_remaining = b["remaining"]
        if best_bin:
            best_bin["items"].append(item_size)
            best_bin["remaining"] -= item_size
        else:
            bins.append({"items": [item_size], "remaining": bin_capacity - item_size})
    return bins


def bin_packing_decision(cpu_map, mode="FFD"):
    """
    Calcule le nombre optimal de replicas par service
    selon la stratégie bin packing choisie.
    
    mode : "FF", "FFD", "BF", "BFD"
    """
    decisions = {}
    
    items = [(service, cpu) for service, cpu in cpu_map.items()]
    
    if mode in ["FFD", "BFD"]:
        items.sort(key=lambda x: x[1], reverse=True)
    
    for service, cpu in items:
        if cpu <= 0.01:
            decisions[service] = MIN_REPLICAS
        else:
            needed = int((cpu / (NODE_CAPACITY * 0.8)) + 1)
            decisions[service] = max(MIN_REPLICAS, min(needed, MAX_REPLICAS))
    
    sizes = [cpu for _, cpu in items]
    if mode in ["FF", "FFD"]:
        bins = first_fit(sizes, NODE_CAPACITY)
    else:
        bins = best_fit(sizes, NODE_CAPACITY)
    
    logging.info(f"📦 Mode {mode}: {len(bins)} bins utilisés pour {len(items)} services")
    
    return decisions


def run(mode="FFD"):
    logging.info(f"🚀 Démarrage Bin Packing Autoscaler — Mode: {mode}")
    
    while True:
        cpu_map = {svc: get_service_cpu(svc) for svc in SERVICES}
        
        decisions = bin_packing_decision(cpu_map, mode)
        
        for service, target_replicas in decisions.items():
            current = get_current_replicas(service)
            if current != target_replicas:
                logging.info(f"🔄 {service}: {current} → {target_replicas} replicas (CPU={cpu_map[service]:.2%})")
                scale_deployment(service, target_replicas)
        
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "FFD"
    run(mode)