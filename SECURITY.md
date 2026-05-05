# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| main    | ✅        |

## Reporting a Vulnerability

Si tu découvres une vulnérabilité dans ce projet :

1. **Ne pas créer d'issue publique**
2. Envoie un email à : security@pfe-devsecops.local
3. Inclure :
   - Description de la vulnérabilité
   - Étapes pour reproduire
   - Impact potentiel
   - Suggestion de correction si possible

## Délai de réponse

- Accusé de réception : 48h
- Évaluation initiale : 5 jours ouvrés
- Correctif : selon criticité (critique = 24h, haute = 7 jours)

## Politique de divulgation

Divulgation coordonnée après correction déployée.

## Outils de sécurité actifs

- Gitleaks : détection secrets dans le code
- Trivy : scan vulnérabilités images Docker
- SonarCloud : analyse statique du code
- OWASP ZAP : tests dynamiques de sécurité
- OPA Gatekeeper : politiques Kubernetes
- Sealed Secrets : chiffrement des secrets Git
