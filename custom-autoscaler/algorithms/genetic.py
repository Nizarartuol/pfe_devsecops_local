"""
ALGORITHME 6 — GENETIC ALGORITHM (GA)
=======================================
Principe : Inspiré de la sélection naturelle de Darwin.

Étapes du cycle génétique :
1. Population initiale : configurations aléatoires de replicas
2. Évaluation (fitness) : score de chaque configuration
3. Sélection : garder les meilleures configurations
4. Croisement (crossover) : combiner deux configurations parents
5. Mutation : modifier aléatoirement pour explorer
6. Répéter jusqu'à convergence

Un "chromosome" = une configuration complète de replicas
  ex: [frontend=2, adservice=1, cartservice=3, ...]

La sélection naturelle converge vers la configuration
qui maximise les performances tout en minimisant le coût.

Différence avec PSO :
- PSO : particules qui se déplacent continûment
- GA : population qui évolue par génération
"""

import subprocess
import time
import logging
import numpy as np
import random

# 🔥 IMPORT NORMALIZER
from metrics.metrics_normalizer import get_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s [GENETIC] %(message)s')

NAMESPACE = "dev"
INTERVAL_SECONDS = 30

# GA Parameters
POPULATION_SIZE = 20
N_GENERATIONS = 15
MUTATION_RATE = 0.15
CROSSOVER_RATE = 0.8
ELITE_SIZE = 4
MIN_REPLICAS = 1
MAX_REPLICAS = 5

SERVICES = [
    "frontend", "adservice", "cartservice", "checkoutservice",
    "currencyservice", "emailservice", "paymentservice",
    "productcatalogservice", "recommendationservice", "shippingservice"
]

N_GENES = len(SERVICES)


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


def fitness(chromosome, cpu_map):
    score = 100.0
    
    for i, service in enumerate(SERVICES):
        replicas = chromosome[i]
        cpu = cpu_map[service]

        capacity_per_replica = 0.8
        total_capacity = replicas * capacity_per_replica

        if cpu > total_capacity:
            deficit = cpu - total_capacity
            score -= deficit * 20
        else:
            surplus = total_capacity - cpu
            score -= surplus * 2

    return max(0, score)


def create_individual():
    return [random.randint(MIN_REPLICAS, MAX_REPLICAS) for _ in range(N_GENES)]


def tournament_selection(population, scores, tournament_size=3):
    tournament = random.sample(range(len(population)), tournament_size)
    winner = max(tournament, key=lambda i: scores[i])
    return population[winner].copy()


def crossover(parent1, parent2):
    if random.random() > CROSSOVER_RATE:
        return parent1.copy(), parent2.copy()
    
    point = random.randint(1, N_GENES - 1)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2


def mutate(chromosome):
    mutated = chromosome.copy()
    for i in range(N_GENES):
        if random.random() < MUTATION_RATE:
            mutated[i] = random.randint(MIN_REPLICAS, MAX_REPLICAS)
    return mutated


def genetic_optimize(cpu_map):
    population = [create_individual() for _ in range(POPULATION_SIZE)]
    
    best_ever = None
    best_score_ever = -1
    
    for generation in range(N_GENERATIONS):
        scores = [fitness(ind, cpu_map) for ind in population]
        
        best_idx = np.argmax(scores)
        if scores[best_idx] > best_score_ever:
            best_score_ever = scores[best_idx]
            best_ever = population[best_idx].copy()
        
        elite_indices = np.argsort(scores)[-ELITE_SIZE:]
        new_population = [population[i].copy() for i in elite_indices]
        
        while len(new_population) < POPULATION_SIZE:
            parent1 = tournament_selection(population, scores)
            parent2 = tournament_selection(population, scores)
            child1, child2 = crossover(parent1, parent2)
            child1 = mutate(child1)
            child2 = mutate(child2)
            new_population.extend([child1, child2])
        
        population = new_population[:POPULATION_SIZE]
    
    logging.info(f"🧬 GA terminé — Score final: {best_score_ever:.2f}")
    
    return {SERVICES[i]: best_ever[i] for i in range(N_GENES)}


def run():
    logging.info("🚀 Démarrage Genetic Algorithm Autoscaler")

    while True:
        # 🔥 UTILISATION NORMALIZER
        metrics = get_metrics()
        cpu_map = metrics["cpu"]

        logging.info("📊 CPU actuel: " +
                     ", ".join(f"{s}={v:.2%}" for s, v in cpu_map.items()))
        
        optimal_config = genetic_optimize(cpu_map)
        
        logging.info("🎯 Configuration optimale:")
        for service, replicas in optimal_config.items():
            current = get_current_replicas(service)
            logging.info(f"{service}: {current} → {replicas}")
            if current != replicas:
                scale_deployment(service, replicas)
        
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    run()