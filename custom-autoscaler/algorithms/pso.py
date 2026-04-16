"""
ALGORITHME 5 — PARTICLE SWARM OPTIMIZATION (PSO)
==================================================
Principe : Inspiré du comportement des nuées d'oiseaux
ou bancs de poissons. Chaque "particule" est une
solution candidate (une configuration de replicas).

Les particules :
1. Explorent l'espace de solutions
2. Se souviennent de leur meilleure position
3. Sont attirées vers la meilleure position globale
4. Convergent vers la solution optimale

Dans notre contexte :
- Une particule = une configuration [replicas_svc1, replicas_svc2, ...]
- La "fitness" = performance - coût (minimiser le coût tout en
  gardant les performances acceptables)

PSO trouve la configuration optimale de replicas qui
maximise la performance tout en minimisant le coût.
"""

import subprocess
import time
import logging
import numpy as np
import random

# ✅ NORMALIZER
from metrics.metrics_normalizer import get_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [PSO] %(message)s')

NAMESPACE = "dev"
INTERVAL_SECONDS = 30

N_PARTICLES = 10
N_ITERATIONS = 20
W = 0.7
C1 = 1.5
C2 = 1.5
MIN_REPLICAS = 1
MAX_REPLICAS = 5

SERVICES = [
    "frontend", "adservice", "cartservice", "checkoutservice",
    "currencyservice", "emailservice", "paymentservice",
    "productcatalogservice", "recommendationservice", "shippingservice"
]

N_SERVICES = len(SERVICES)


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


# ❌ SUPPRIMÉ : get_all_cpu()


def fitness_function(position, cpu_map):
    """ 
    Fonction d'évaluation d'une configuration (particule). 

    Objectifs contradictoires à équilibrer : 
    1. Performance : assez de replicas pour gérer la charge 
    2. Coût : le moins de replicas possible 

    Score = performance_score - cost_penalty 

    Plus le score est haut, meilleure est la configuration. 
    """
    
    performance_score = 0.0
    cost_penalty = 0.0

    for i, service in enumerate(SERVICES):
        replicas = int(round(position[i]))
        cpu = cpu_map.get(service, 0.0)

        capacity = replicas * 0.8

        if cpu > capacity:
            performance_score -= (cpu - capacity) * 10
        else:
            performance_score += 1.0

        cost_penalty += max(0, capacity - cpu) * 0.5

    return performance_score - cost_penalty


def pso_optimize(cpu_map):
    """
     Optimisation PSO pour trouver la meilleure configuration de replicas.
     Retourne la meilleure configuration trouvée.
      """

    particles = np.random.uniform(MIN_REPLICAS, MAX_REPLICAS,
                                  (N_PARTICLES, N_SERVICES))
    velocities = np.zeros((N_PARTICLES, N_SERVICES))

    personal_best = particles.copy()
    personal_best_scores = np.array([
        fitness_function(p, cpu_map) for p in particles
    ])

    global_best_idx = np.argmax(personal_best_scores)
    global_best = personal_best[global_best_idx].copy()
    global_best_score = personal_best_scores[global_best_idx]

    logging.info(f"PSO Initial — Best score: {global_best_score:.4f}")

    for iteration in range(N_ITERATIONS):
        for i in range(N_PARTICLES):
            r1 = random.random()
            r2 = random.random()

            velocities[i] = (W * velocities[i] +
                            C1 * r1 * (personal_best[i] - particles[i]) +
                            C2 * r2 * (global_best - particles[i]))

            particles[i] = np.clip(
                particles[i] + velocities[i],
                MIN_REPLICAS,
                MAX_REPLICAS
            )

            score = fitness_function(particles[i], cpu_map)

            if score > personal_best_scores[i]:
                personal_best[i] = particles[i].copy()
                personal_best_scores[i] = score

                if score > global_best_score:
                    global_best = particles[i].copy()
                    global_best_score = score

    logging.info(f"PSO Final — Best score: {global_best_score:.4f}")

    return {
        SERVICES[i]: max(
            MIN_REPLICAS,
            min(MAX_REPLICAS, int(round(global_best[i])))
        )
        for i in range(N_SERVICES)
    }


def run():
    logging.info("🚀 Démarrage PSO Autoscaler")
    logging.info(f"Particules: {N_PARTICLES}, Iterations: {N_ITERATIONS}")

    last_metrics = {}

    while True:
        # ✅ REMPLACÉ : une seule source de vérité
        metrics = get_metrics()

        cpu_map = {
            svc: metrics.get(svc, {}).get("cpu_percent", 0.0)
            for svc in SERVICES
        }

        logging.info("📊 CPU actuel: " +
                     ", ".join(f"{s}={v:.2%}" for s, v in cpu_map.items()))

        logging.info("🔄 Optimisation PSO en cours...")
        optimal_config = pso_optimize(cpu_map)

        logging.info("🎯 Configuration optimale PSO:")
        for service, replicas in optimal_config.items():
            current = get_current_replicas(service)
            logging.info(f"  {service}: {current} → {replicas}")
            if current != replicas:
                scale_deployment(service, replicas)

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run()