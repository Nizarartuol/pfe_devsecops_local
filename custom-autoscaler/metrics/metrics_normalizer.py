import requests

PROMETHEUS_URL = "http://localhost:9090"
NAMESPACE = "dev"


# ─────────────────────────────────────────────
# CORE PROMETHEUS QUERY
# ─────────────────────────────────────────────
def query_prometheus(query: str):
    """Exécute une requête Prometheus et retourne la valeur."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        data = response.json()

        if data["status"] != "success":
            return None

        result = data["data"]["result"]
        if not result:
            return None

        return float(result[0]["value"][1])

    except Exception:
        return None


# ─────────────────────────────────────────────
# CPU USAGE (RAW)
# ─────────────────────────────────────────────
def get_cpu_usage(service: str):
    query = f'''
    sum(rate(container_cpu_usage_seconds_total{{
        namespace="{NAMESPACE}",
        pod=~"{service}-.*"
    }}[2m]))
    '''

    value = query_prometheus(query)
    return value if value is not None else 0.0


# ─────────────────────────────────────────────
# CPU REQUEST (K8S reference for %)
# ─────────────────────────────────────────────
def get_cpu_request(service: str):
    query = f'''
    sum(kube_pod_container_resource_requests_cpu_cores{{
        namespace="{NAMESPACE}",
        pod=~"{service}-.*"
    }})
    '''

    value = query_prometheus(query)
    return value if value is not None else 0.1  # avoid division by zero


# ─────────────────────────────────────────────
# CPU UTILIZATION (% NORMALIZED)
# ─────────────────────────────────────────────
def get_cpu_percent(service: str):
    usage = get_cpu_usage(service)
    request = get_cpu_request(service)

    if request == 0:
        return 0.0

    return (usage / request) * 100


# ─────────────────────────────────────────────
# MEMORY (OPTIONAL FOR FUTURE ALGORITHMS)
# ─────────────────────────────────────────────
def get_memory_usage(service: str):
    query = f'''
    sum(container_memory_usage_bytes{{
        namespace="{NAMESPACE}",
        pod=~"{service}-.*"
    }})
    '''

    value = query_prometheus(query)
    return value if value is not None else 0.0


def get_memory_request(service: str):
    query = f'''
    sum(kube_pod_container_resource_requests_memory_bytes{{
        namespace="{NAMESPACE}",
        pod=~"{service}-.*"
    }})
    '''

    value = query_prometheus(query)
    return value if value is not None else 1


def get_memory_percent(service: str):
    usage = get_memory_usage(service)
    request = get_memory_request(service)

    if request == 0:
        return 0.0

    return (usage / request) * 100


# ─────────────────────────────────────────────
# FINAL UNIFIED METRIC OBJECT
# ─────────────────────────────────────────────
def get_metrics(service: str):
    """
    Retourne un format standard pour tous les algorithmes.
    """
    return {
        "cpu_percent": get_cpu_percent(service),
        "cpu_usage_raw": get_cpu_usage(service),
        "memory_percent": get_memory_percent(service),
    }