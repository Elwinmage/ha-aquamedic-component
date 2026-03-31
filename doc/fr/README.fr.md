# Aquamedic
> Fait partie de l'**[Écosystème ReefTech Project](https://elwinmage.github.io/reeftank/fr.html)**
<p align="center">
  <img src="icon.png" width="50%"/>
</p>
[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/hacs)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Cloud%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-aquamedic-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-aquamedic-component/releases)
[![Ruff Status](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-aquamedic-component)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-aquamedic-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-aquamedic-component)
![Installations](https://img.shields.io/badge/dynamic/json?label=Active%20Installs&query=estimated&cacheSeconds=3600&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-aquamedic-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)

# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/it/README.it.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/pt/README.pt.md)

Contrôlez vos pompes Aqua Medic depuis Home Assistant via l'API cloud Gizwits.

---

## Appareils compatibles

Votre appareil n'est pas supporté ? Contactez-moi.

> ✅ Supporté &nbsp;|&nbsp; 🧪 Non testé (peut fonctionner) &nbsp;|&nbsp; ❌ Pas encore supporté

| Appareil | | Nom interne | Clé produit | Statut |
|---|---|---|---|---|

| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (pompe de remontée) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Tous ces appareils utilisent la plateforme IoT Gizwits (même backend que l'application officielle Aqua Medic). La prise en charge d'appareils supplémentaires pourra être ajoutée dans de futures versions.

---

## Installation

### Via HACS (recommandé)

1. Dans HACS, aller dans **Intégrations → ⋮ → Dépôts personnalisés**
2. Ajouter `https://github.com/Elwinmage/ha-aquamedic-component` en tant qu'**Intégration**
3. Rechercher **Aqua Medic** et installer
4. Redémarrer Home Assistant

---

## Entités

### EcoDrift / SmartDrift

#### Interrupteurs

| Entité | Description |
|---|---|
| **Alimentation** | Marche/arrêt principal |
| **Type de vague** | Mode impulsion (off) / Mode marée (on) |
| **Mode nourrissage** | Active la pause de nourrissage |
| **Minuterie** | Active le mode programme |
| **Mode contrôle 0-10V** | Quand activé, désactive le curseur de débit (pompe pilotée par signal externe 0-10V) |

#### Listes de sélection

| Entité | Options |
|---|---|
| **Mode vague** | Vague classique · Vague sinusoïdale · Vague aléatoire · Débit constant |
| **Couplage** | Indépendant · Maître · Esclave |

#### Nombres

| Entité | Plage | Description |
|---|---|---|
| **Débit** | 0–100 % | Débit moteur (désactivé en mode 0-10V) |
| **Fréquence** | 0–100 % | Fréquence des vagues |
| **Durée de nourrissage** | 1–60 min | Durée de la pause de nourrissage |

#### Capteurs binaires (diagnostic)

| Entité | Description |
|---|---|
| **Défaut surintensité** | Surintensité / court-circuit moteur |
| **Défaut surtension** | Surtension moteur |
| **Défaut surchauffe** | Température moteur trop élevée |
| **Défaut sous-tension** | Sous-tension moteur |
| **Défaut rotor bloqué** | Moteur grippé / bloqué |
| **Défaut marche à vide** | Pompe fonctionnant à sec |
| **Défaut communication UART** | Erreur de communication module ↔ carte principale |

#### Bouton (diagnostic)

| Entité | Description |
|---|---|
| **Actualiser** | Force une actualisation immédiate sans attendre le prochain cycle d'interrogation |

### DC Runner

> 🧪 Le support est implémenté mais **pas encore testé sur matériel réel**. Retours bienvenus.

#### Interrupteurs

| Entité | Description |
|---|---|
| **Alimentation** | Marche/arrêt principal |
| **Mode nourrissage** | Coupe le débit pendant 10 minutes |
| **Mode contrôle 0-10V** | Quand activé, le débit est piloté par signal externe 0-10V |

#### Nombres

| Entité | Plage | Description |
|---|---|---|
| **Débit** | 30–100 % | Vitesse de la pompe (minimum 30 % — en dessous le moteur peut caler) |

#### Capteurs binaires (diagnostic)

| Entité | Description |
|---|---|
| **Défaut marche à vide** | Arrêt automatique si pas d'eau détectée pendant 2 min |
| **Défaut rotor bloqué** | Obstruction mécanique détectée |
| **Défaut tension** | Tension d'alimentation hors plage |

---

## Configuration

Aller dans **Paramètres → Appareils et services → Ajouter une intégration → Aqua Medic**.

| Champ | Description |
|---|---|
| **E-mail** | Adresse e-mail de votre compte Aqua Medic |
| **Mot de passe** | Mot de passe de votre compte Aqua Medic |
| **Serveur Gizwits** | Serveur régional — sélectionner **Europe** pour les utilisateurs EU |
| **Intervalle d'actualisation** | Fréquence d'interrogation de l'appareil (5–300 s, défaut 30 s) |

Le serveur correct est présélectionné automatiquement en fonction de la langue de Home Assistant.

Après configuration, l'intervalle d'actualisation peut être modifié via **Paramètres → Appareils et services → Aqua Medic → Configurer**.

---

## Licence

MIT – voir [LICENSE](../../LICENSE).

