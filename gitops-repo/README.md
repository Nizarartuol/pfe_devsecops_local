# GitOps Repository – PFE DevSecOps

Ce dépôt contient les manifests Kubernetes surveillés par **ArgoCD**.  
Toute modification commitée ici déclenche automatiquement un redéploiement sur le cluster k3d local.

## Structure

```
gitops-repo/
├── kubernetes-manifests/   # Déploiements des micro-services (Online Boutique)
├── monitoring/             # Prometheus, Grafana, Loki via Helm/Kustomize
└── argocd/                 # Applications ArgoCD
```

## Registry locale

Toutes les images pointent vers la registry k3d locale :  
`registry.localhost:5000/<service>:<tag>`

## Monitoring

Le namespace `monitoring` contient la stack observabilité :
- **Prometheus** – métriques
- **Grafana** – dashboards
- **Loki** – logs

```bash
kubectl apply -f monitoring/namespace.yaml
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack -n monitoring -f monitoring/prometheus-values.yaml
helm upgrade --install loki grafana/loki-stack -n monitoring -f monitoring/loki-values.yaml
```
