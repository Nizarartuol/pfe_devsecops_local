"""
META-CONTROLLER — Orchestrateur Intelligent des Algorithmes
============================================================
Principe : Un seul fichier qui analyse le workload en temps réel
et choisit automatiquement le meilleur algorithme selon le contexte.

Logique de décision basée sur 6 règles expertes :
1. Urgence critique    → Heuristic (service critique en danger)
2. Tendance montante   → Predictive (anticiper avant le pic)
3. Pic soudain         → PSO ou Genetic (optimisation globale)
4. Services inégaux    → Least Loaded (redistribution prioritaire)
5. Coût excessif       → Bin Packing (optimisation ressources)
6. Charge stable       → Threshold (simple et efficace)
"""

import time
import requests
import subprocess
import logging
import numpy as np
from collections import defaultdict, deque
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [META] %(message)s'
)

# ─── Configuration ────────────────────────────────────────────
PROMETHEUS_URL = "http://localhost:9090"
NAMESPACE = "dev"
INTERVAL_SECONDS = 15
HISTORY_SIZE = 10

SERVICES = [
    "frontend", "adservice", "cartservice", "checkoutservice",
    "currencyservice", "emailservice", "paymentservice",
    "productcatalogservice", "recommendationservice", "shippingservice"
]

# Priorités (1 = critique)
SERVICE_PRIORITY = {
    "frontend": 1, "cartservice": 1, "checkoutservice": 1,
    "paymentservice": 2, "productcatalogservice": 2,
    "adservice": 3, "currencyservice": 3, "emailservice": 3,
    "recommendationservice": 3, "shippingservice": 3,
}

# ─── Seuils de décision ───────────────────────────────────────
THRESHOLD_CRITICAL = 0.80      # CPU > 80% → urgence
THRESHOLD_HIGH = 0.65          # CPU > 65% → charge haute
THRESHOLD_STABLE_UP = 0.50     # CPU > 50% → surveiller
THRESHOLD_LOW = 0.25           # CPU < 25% → potentiel scale down
TREND_RISING = 0.05            # hausse > 5% par intervalle
TREND_FALLING = -0.05          # baisse > 5% par intervalle
IMBALANCE_FACTOR = 2.5         # écart max entre services
COST_THRESHOLD = 0.30          # sur-provisionnement > 30% → bin packing
SPIKE_FACTOR = 3.0             # CPU × 3 en un intervalle → pic soudain


class Algorithm(Enum):
    THRESHOLD = "threshold"
    LEAST_LOADED = "least_loaded"
    BIN_PACKING = "bin_packing"
    PREDICTIVE = "predictive"
    PSO = "pso"
    GENETIC = "genetic"
    HEURISTIC = "heuristic"


# ─── Historique des métriques ─────────────────────────────────
cpu_history = defaultdict(lambda: deque(maxlen=HISTORY_SIZE))
algo_history = deque(maxlen=20)
scale_count = defaultdict(int)


# ─── Collecte métriques ───────────────────────────────────────

def get_all_cpu():
    """Récupère CPU de tous les services depuis Prometheus."""
    result = {}
    for svc in SERVICES:
        query = (f'avg(rate(container_cpu_usage_seconds_total'
                 f'{{namespace="{NAMESPACE}",pod=~"{svc}-.*"}}[2m]))')
        try:
            resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                                params={"query": query}, timeout=5)
            data = resp.json()
            if data["data"]["result"]:
                result[svc] = float(data["data"]["result"][0]["value"][1])
            else:
                result[svc] = 0.0
        except:
            result[svc] = 0.0
    return result


def get_replicas(service):
    r = subprocess.run(
        ["kubectl", "get", "deployment", service, "-n", NAMESPACE,
         "-o", "jsonpath={.spec.replicas}"],
        capture_output=True, text=True
    )
    try:
        return int(r.stdout.strip())
    except:
        return 1


def scale(service, replicas):
    r = subprocess.run(
        ["kubectl", "scale", "deployment", service,
         "-n", NAMESPACE, f"--replicas={replicas}"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        scale_count[service] += 1
        logging.info(f"  ✅ {service} → {replicas} replicas")


# ─── Analyse du workload ──────────────────────────────────────

def analyze_workload(cpu_map):
    """
    Analyse le workload actuel et retourne un profil détaillé.
    C'est la "intelligence" du meta-controller.
    """
    values = list(cpu_map.values())
    
    profile = {
        "avg_cpu": np.mean(values),
        "max_cpu": max(values),
        "min_cpu": min(values),
        "std_cpu": np.std(values),
        "critical_services": [],
        "overloaded_services": [],
        "idle_services": [],
        "imbalance_ratio": 0.0,
        "trend": "stable",
        "spike_detected": False,
        "cost_waste": 0.0,
        "total_replicas": 0,
    }
    
    # Identifier les services par état
    for svc, cpu in cpu_map.items():
        priority = SERVICE_PRIORITY.get(svc, 3)
        replicas = get_replicas(svc)
        profile["total_replicas"] += replicas
        
        if cpu > THRESHOLD_CRITICAL and priority == 1:
            profile["critical_services"].append(svc)
        if cpu > THRESHOLD_HIGH:
            profile["overloaded_services"].append(svc)
        if cpu < THRESHOLD_LOW:
            profile["idle_services"].append(svc)
        
        # Calculer le gaspillage (over-provisioning)
        capacity = replicas * 0.8
        if capacity > 0:
            waste = max(0, (capacity - cpu) / capacity)
            profile["cost_waste"] += waste
    
    profile["cost_waste"] /= len(SERVICES)
    
    # Ratio déséquilibre entre services
    if profile["min_cpu"] > 0:
        profile["imbalance_ratio"] = profile["max_cpu"] / profile["min_cpu"]
    
    # Tendance globale (moyenne des tendances individuelles)
    trends = []
    for svc, history in cpu_history.items():
        if len(history) >= 3:
            recent = np.mean(list(history)[-3:])
            old = np.mean(list(history)[:3])
            trends.append(recent - old)
    
    if trends:
        avg_trend = np.mean(trends)
        if avg_trend > TREND_RISING:
            profile["trend"] = "rising"
        elif avg_trend < TREND_FALLING:
            profile["trend"] = "falling"
    
    # Détection de spike (hausse soudaine × 3)
    for svc, history in cpu_history.items():
        if len(history) >= 2:
            prev = list(history)[-2]
            curr = cpu_map.get(svc, 0)
            if prev > 0.01 and curr > prev * SPIKE_FACTOR:
                profile["spike_detected"] = True
                break
    
    return profile


# ─── Sélection de l'algorithme ────────────────────────────────

def select_algorithm(profile, cpu_map):
    """
    Règles de sélection par priorité décroissante.
    Retourne (Algorithm, raison, config)
    """
    
    # RÈGLE 1 — Service critique en danger → Heuristic
    # Priorité absolue : si frontend/cart/checkout > 80%
    if profile["critical_services"]:
        return (
            Algorithm.HEURISTIC,
            f"Services critiques en danger: {profile['critical_services']}",
            {}
        )
    
    # RÈGLE 2 — Pic soudain → PSO (si charge légère) ou Genetic (si charge lourde)
    if profile["spike_detected"]:
        if profile["avg_cpu"] > THRESHOLD_HIGH:
            return (
                Algorithm.GENETIC,
                f"Pic soudain détecté, charge haute ({profile['avg_cpu']:.1%})",
                {}
            )
        else:
            return (
                Algorithm.PSO,
                f"Pic soudain détecté, charge modérée ({profile['avg_cpu']:.1%})",
                {}
            )
    
    # RÈGLE 3 — Tendance montante → Predictive
    if (profile["trend"] == "rising" and
            profile["avg_cpu"] > THRESHOLD_STABLE_UP):
        return (
            Algorithm.PREDICTIVE,
            f"Tendance montante détectée (avg={profile['avg_cpu']:.1%})",
            {}
        )
    
    # RÈGLE 4 — Déséquilibre fort entre services → Least Loaded
    if profile["imbalance_ratio"] > IMBALANCE_FACTOR:
        return (
            Algorithm.LEAST_LOADED,
            f"Déséquilibre fort entre services (ratio={profile['imbalance_ratio']:.1f}x)",
            {}
        )
    
    # RÈGLE 5 — Gaspillage coût excessif → Bin Packing
    if profile["cost_waste"] > COST_THRESHOLD:
        return (
            Algorithm.BIN_PACKING,
            f"Sur-provisionnement détecté ({profile['cost_waste']:.1%} gaspillage)",
            {"mode": "BFD"}  # Best Fit Decreasing pour optimiser
        )
    
    # RÈGLE 6 — Charge stable → Threshold (simple et fiable)
    return (
        Algorithm.THRESHOLD,
        f"Charge stable (avg={profile['avg_cpu']:.1%}, trend={profile['trend']})",
        {}
    )


# ─── Exécution des algorithmes ────────────────────────────────

def run_threshold(cpu_map):
    """Threshold simple : scale si CPU > 70% ou < 30%."""
    for svc, cpu in cpu_map.items():
        replicas = get_replicas(svc)
        if cpu > 0.70 and replicas < 5:
            scale(svc, replicas + 1)
        elif cpu < 0.30 and replicas > 1:
            scale(svc, replicas - 1)


def run_least_loaded(cpu_map):
    """Priorise les resources vers les services les plus chargés."""
    sorted_services = sorted(cpu_map.items(), key=lambda x: x[1], reverse=True)
    scaled = 0
    for svc, cpu in sorted_services:
        if scaled >= 2:
            break
        replicas = get_replicas(svc)
        if cpu > 0.65 and replicas < 5:
            scale(svc, replicas + 1)
            scaled += 1
    for svc, cpu in sorted_services:
        replicas = get_replicas(svc)
        if cpu < 0.20 and replicas > 1:
            scale(svc, replicas - 1)


def run_bin_packing(cpu_map, mode="BFD"):
    """Optimise le placement pour minimiser les ressources utilisées."""
    for svc, cpu in cpu_map.items():
        replicas = get_replicas(svc)
        if cpu <= 0.01:
            target = 1
        else:
            target = max(1, min(5, int(cpu / 0.65) + 1))
        if target != replicas:
            scale(svc, target)


def run_predictive(cpu_map):
    """Scale basé sur la prédiction linéaire."""
    for svc in SERVICES:
        history = cpu_history[svc]
        if len(history) < 3:
            continue
        x = np.arange(len(history))
        y = np.array(list(history))
        coeffs = np.polyfit(x, y, 1)
        predicted = np.polyval(coeffs, len(history) + 4)
        predicted = max(0.0, min(1.0, predicted))
        
        replicas = get_replicas(svc)
        if predicted > 0.60 and replicas < 5:
            scale(svc, replicas + 1)
        elif predicted < 0.25 and replicas > 1:
            scale(svc, replicas - 1)


def run_pso(cpu_map):
    """PSO simplifié — convergence rapide pour les spikes."""
    n_particles = 8
    n_iter = 10
    n_svc = len(SERVICES)
    
    particles = np.random.uniform(1, 5, (n_particles, n_svc))
    velocities = np.zeros((n_particles, n_svc))
    
    def fitness(pos):
        score = 0
        for i, svc in enumerate(SERVICES):
            r = int(round(pos[i]))
            cpu = cpu_map[svc]
            cap = r * 0.8
            if cpu > cap:
                score -= (cpu - cap) * 15
            else:
                score += 1 - (cap - cpu) * 0.5
        return score
    
    pb = particles.copy()
    pb_scores = np.array([fitness(p) for p in particles])
    gb = pb[np.argmax(pb_scores)].copy()
    gb_score = max(pb_scores)
    
    for _ in range(n_iter):
        for i in range(n_particles):
            r1, r2 = np.random.random(2)
            velocities[i] = (0.7 * velocities[i] +
                             1.5 * r1 * (pb[i] - particles[i]) +
                             1.5 * r2 * (gb - particles[i]))
            particles[i] = np.clip(particles[i] + velocities[i], 1, 5)
            s = fitness(particles[i])
            if s > pb_scores[i]:
                pb[i] = particles[i].copy()
                pb_scores[i] = s
                if s > gb_score:
                    gb = particles[i].copy()
                    gb_score = s
    
    for i, svc in enumerate(SERVICES):
        target = max(1, min(5, int(round(gb[i]))))
        current = get_replicas(svc)
        if current != target:
            scale(svc, target)


def run_genetic(cpu_map):
    """Genetic Algorithm pour configuration complexe."""
    pop_size = 15
    n_gen = 10
    n_svc = len(SERVICES)
    
    def fitness(chrom):
        score = 100.0
        for i, svc in enumerate(SERVICES):
            r = chrom[i]
            cpu = cpu_map[svc]
            cap = r * 0.8
            if cpu > cap:
                score -= (cpu - cap) * 20
            else:
                score -= max(0, cap - cpu) * 2
        return max(0, score)
    
    pop = [[np.random.randint(1, 6) for _ in range(n_svc)]
           for _ in range(pop_size)]
    
    for _ in range(n_gen):
        scores = [fitness(ind) for ind in pop]
        elite = sorted(range(pop_size), key=lambda i: scores[i], reverse=True)[:4]
        new_pop = [pop[i].copy() for i in elite]
        
        while len(new_pop) < pop_size:
            p1 = pop[np.random.choice(elite)]
            p2 = pop[np.random.choice(elite)]
            pt = np.random.randint(1, n_svc)
            child = p1[:pt] + p2[pt:]
            for j in range(n_svc):
                if np.random.random() < 0.15:
                    child[j] = np.random.randint(1, 6)
            new_pop.append(child)
        pop = new_pop
    
    scores = [fitness(ind) for ind in pop]
    best = pop[np.argmax(scores)]
    for i, svc in enumerate(SERVICES):
        target = max(1, min(5, best[i]))
        current = get_replicas(svc)
        if current != target:
            scale(svc, target)


def run_heuristic(cpu_map):
    """Heuristique hybride avec priorité services critiques."""
    for svc in SERVICES:
        cpu = cpu_map[svc]
        priority = SERVICE_PRIORITY.get(svc, 3)
        replicas = get_replicas(svc)
        history = list(cpu_history[svc])
        
        trend = "stable"
        if len(history) >= 3:
            if np.mean(history[-2:]) > np.mean(history[:2]) + 0.05:
                trend = "rising"
        
        threshold_up = 0.60 if priority == 1 else 0.70
        threshold_down = 0.20 if priority == 1 else 0.25
        
        if cpu > 0.85 and replicas < 5:
            scale(svc, replicas + 1)
        elif trend == "rising" and cpu > threshold_up and replicas < 5:
            scale(svc, replicas + 1)
        elif cpu > threshold_up and replicas < 5:
            scale(svc, replicas + 1)
        elif cpu < threshold_down and replicas > 1:
            scale(svc, replicas - 1)


# ─── Dispatch vers l'algorithme choisi ───────────────────────

def dispatch(algo, cpu_map, config):
    """Exécute l'algorithme sélectionné."""
    dispatch_map = {
        Algorithm.THRESHOLD:    lambda: run_threshold(cpu_map),
        Algorithm.LEAST_LOADED: lambda: run_least_loaded(cpu_map),
        Algorithm.BIN_PACKING:  lambda: run_bin_packing(cpu_map, config.get("mode", "FFD")),
        Algorithm.PREDICTIVE:   lambda: run_predictive(cpu_map),
        Algorithm.PSO:          lambda: run_pso(cpu_map),
        Algorithm.GENETIC:      lambda: run_genetic(cpu_map),
        Algorithm.HEURISTIC:    lambda: run_heuristic(cpu_map),
    }
    dispatch_map[algo]()


# ─── Boucle principale ────────────────────────────────────────

def run():
    logging.info("🚀 Meta-Controller démarré")
    logging.info("Surveillance: " + ", ".join(SERVICES))
    
    last_algo = None
    algo_switch_count = 0
    
    try:
        while True:
            # 1. Collecter métriques
            cpu_map = get_all_cpu()
            
            # 2. Mettre à jour historique
            for svc, cpu in cpu_map.items():
                cpu_history[svc].append(cpu)
            
            # 3. Analyser le workload
            profile = analyze_workload(cpu_map)
            
            # 4. Sélectionner l'algorithme
            algo, reason, config = select_algorithm(profile, cpu_map)
            
            # 5. Logger le changement d'algorithme
            if algo != last_algo:
                algo_switch_count += 1
                logging.info(f"\n{'='*55}")
                logging.info(f"🔄 CHANGEMENT ALGO #{algo_switch_count}: "
                             f"{last_algo.value if last_algo else 'None'} → {algo.value.upper()}")
                logging.info(f"   Raison: {reason}")
                logging.info(f"{'='*55}")
                last_algo = algo
            else:
                logging.info(f"\n📌 Algo actif: {algo.value.upper()} | {reason}")
            
            # 6. Afficher le profil workload
            logging.info(f"   CPU moy={profile['avg_cpu']:.1%} "
                         f"max={profile['max_cpu']:.1%} "
                         f"trend={profile['trend']} "
                         f"spike={profile['spike_detected']} "
                         f"waste={profile['cost_waste']:.1%}")
            
            # 7. Exécuter l'algorithme
            logging.info(f"   Exécution {algo.value}...")
            dispatch(algo, cpu_map, config)
            
            # 8. Enregistrer dans l'historique
            algo_history.append({
                "time": time.time(),
                "algo": algo.value,
                "avg_cpu": profile["avg_cpu"],
                "reason": reason
            })
            
            time.sleep(INTERVAL_SECONDS)
    
    except KeyboardInterrupt:
        logging.info("\n⛔ Meta-Controller arrêté proprement.")
        logging.info(f"Résumé: {algo_switch_count} changements d'algorithme")
        logging.info(f"Scales effectués: {dict(scale_count)}")


if __name__ == "__main__":
    run()
