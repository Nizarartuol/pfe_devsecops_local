# SBOM — Software Bill of Materials

## Définition
Le SBOM est un inventaire exhaustif et formel de toutes les 
composantes logicielles d'un système : dépendances, bibliothèques, 
versions, licences et origines.

## Formats utilisés
- SPDX JSON : standard Linux Foundation, utilisé par GitHub
- CycloneDX JSON : standard OWASP, orienté sécurité

## Outils
- Syft (Anchore) : génération du SBOM
- Grype (Anchore) : scan de vulnérabilités sur le SBOM

## Où trouver les SBOMs générés
GitHub Actions → onglet Artifacts après chaque run du workflow
sbom-generation.yml

## Cas d'usage
Quand une CVE critique est publiée (ex: Log4Shell), le SBOM permet
d'identifier en quelques secondes quels microservices utilisent
la bibliothèque vulnérable.