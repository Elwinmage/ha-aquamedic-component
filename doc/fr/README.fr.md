# Aquamedic
> Fait partie de l'**[Écosystème ReefTech Project](https://elwinmage.github.io/reeftank/fr.html)**
<p align="center">
  <img src="../../icon.png" width="50%"/>
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

<!-- ecosystem:start -->

## Projets liés

Les projets ReefTech s'articulent entre eux : les intégrations font entrer votre matériel dans Home Assistant, la carte l'affiche et le pilote, et le secours le maintient en marche pendant une coupure. Chacun fonctionne aussi seul.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projet</th>
    <th>Rôle</th>
    <th>Fonctionne avec</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reefbeat-component"><b>ha-reefbeat-component</b></a></td>
    <td>Appareils Red Sea ReefBeat, pilotés en local sans cloud : ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun et ReefWave.<br />Fournit <b>ReefBeat watch</b>, un blueprint d'alertes pour les maintenances dépassées, les modes anormaux, les batteries faibles et les appareils injoignables. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td><b>ha-aquamedic-component</b><br /><i>(ce dépôt)</i></td>
    <td>Pompes Aqua Medic via l'API cloud Gizwits : brasseurs EcoDrift et SmartDrift, pompes DC Runner de remontée et d'écumeur.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Suivi du nettoyage et de l'usure du matériel que Home Assistant ne peut pas interroger : pompes de brassage, pompes de remontée, écumeurs, réacteurs, tout ce que vous entretenez à la main.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Vue graphique interactive de chaque appareil sur votre tableau de bord, et seul moyen d'éditer les programmes avancés. Lit les trois intégrations ci-dessus via le contrat <code>reef_role</code> commun, sans configuration côté carte.</td>
    <td>les trois intégrations</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Secours sur batterie en cas de coupure. Pack 24V LiFePO₄ piloté par un Raspberry Pi, avec dégradation progressive de la vitesse des pompes selon l'état de charge.</td>
    <td>seul, ou avec ha-reefbeat-component</td>
  </tr>
</table>

L'ensemble est documenté sur la [page du projet ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

## Appareils compatibles

Votre appareil n'est pas supporté ? Contactez-moi.

> ✅ Supporté &nbsp;|&nbsp; 🧪 Non testé (peut fonctionner) &nbsp;|&nbsp; ❌ Pas encore supporté

| Appareil | | Nom interne | Clé produit | Statut |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (pompe de remontée) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic DC Runner (pompe d'écumeur) | <img alt="écumeur" src="doc/img/skimmer.png" width="200" /> | `DC_Runner` | `00276aa006684c05805c297f60058c3d` | ✅ |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Tous ces appareils utilisent la plateforme IoT Gizwits (même backend que l'application officielle Aqua Medic). La prise en charge d'appareils supplémentaires pourra être ajoutée dans de futures versions.

---

## Installation

### Via HACS

L'intégration est maintenant officiellement dans HACS. Cherchez simplement **Aqua Medic** dans l'onglet Intégrations et installez.

Ou utilisez le bouton d'installation directe :

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-aquamedic-component&category=integration)

Puis redémarrez Home Assistant.

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

### DC Runner (pompe de remontée)

> 🧪 Le support est implémenté mais **pas encore testé sur matériel réel**. Retours bienvenus.

#### Interrupteurs

| Entité | Description |
|---|---|
| **Alimentation** | Marche/arrêt principal |
| **Mode nourrissage** | Coupe le débit pendant 10 minutes |
| **Mode contrôle 0-10V** | Quand activé, désactive le curseur de vitesse (pompe pilotée par signal externe 0-10V) |

#### Nombres

| Entité | Plage | Description |
|---|---|---|
| **Débit** | 30–100 % | Vitesse de la pompe (minimum 30 % — en dessous le moteur peut caler) |

### DC Skimmer (pompe d'écumeur DC Runner)

> ✅ Basé sur une capture réelle des datapoints de l'appareil.

#### Interrupteurs

| Entité | Description |
|---|---|
| **Alimentation** | Marche/arrêt principal |
| **Mode nourrissage** | Active la pause de nourrissage |
| **Minuterie** | Active le programme horaire |
| **Mode contrôle 0-10V** | Quand activé, désactive le curseur de vitesse (pompe pilotée par signal externe 0-10V) |

#### Listes de sélection

| Entité | Options |
|---|---|
| **Mode programmé** | Arrêt · Automatique · Nourrissage |

#### Nombres

| Entité | Plage | Description |
|---|---|---|
| **Vitesse du moteur** | 30–100 % | Vitesse de la pompe (minimum 30 % — en dessous le moteur peut caler ; désactivé en mode 0-10V) |
| **Durée de nourrissage** | 1–60 min | Durée de la pause de nourrissage |
| **Vitesse programmée** | 0–100 % | Vitesse utilisée par le programme horaire |
| **Durée de nourrissage programmée** | 1–60 min | Durée de nourrissage utilisée par le programme horaire |

#### Capteurs binaires (diagnostic)

| Entité | Description |
|---|---|
| **Défaut surintensité** | Surintensité moteur / court-circuit |
| **Défaut surtension** | Surtension moteur |
| **Défaut surchauffe** | Température moteur trop élevée |
| **Défaut sous-tension** | Sous-tension moteur |
| **Défaut rotor bloqué** | Moteur coincé / bloqué |
| **Défaut marche à vide** | Pompe tournant à sec |
| **Défaut communication UART** | Erreur de communication module ↔ carte principale |

#### Bouton (diagnostic)

| Entité | Description |
|---|---|
| **Actualiser** | Force une actualisation immédiate des données |

> **À propos du contrôle 0-10V :** chaque contrôleur DC Runner possède une entrée physique 0-10V destinée à un contrôleur d'aquarium externe (Apex, GHL, …). C'est un port matériel, pas une valeur cloud : il n'apparaît donc pas comme attribut de l'appareil — l'interrupteur *Mode contrôle 0-10V* est un drapeau local Home Assistant qui désactive le curseur de vitesse pendant que la pompe est pilotée en externe. D'après le manuel Aqua Medic, en mode 0-10V la pompe doit tourner à **≥ 60 %**.

---

<!-- maintenance-section:start -->

## Maintenance

L'intégration suit les tâches de nettoyage et d'usure de chaque pompe. Chaque tâche expose trois entités : un **bouton** pour enregistrer que c'est fait, un **curseur** pour ajuster l'intervalle, et un **interrupteur** pour couper ses alertes. Rien n'est envoyé au cloud — l'état est stocké localement, par entrée de configuration.

La pompe de remontée DC Runner et l'écumeur DC Skimmer partagent le même firmware et la même product key Gizwits : l'API ne peut pas les distinguer. Déclarez-le une fois via le select **Rôle de la pompe**, la liste des tâches suit (l'intégration se recharge pour l'appliquer). Tant que le rôle est *Non défini*, une DC Runner n'a aucune tâche. Les EcoDrift / SmartDrift ne posent jamais la question.

| Pompe | Tâche | Défaut | Plage |
|---|---|---|---|
| EcoDrift / SmartDrift | Nettoyer le rotor et le panier de filtration | 2 | 1–3 |
| EcoDrift / SmartDrift | Détartrer la pompe | 6 | 3–9 |
| EcoDrift / SmartDrift | Remplacer le rotor et les roulements | 18 | 12–24 |
| DC Runner (remontée) | Nettoyer la crépine d'aspiration | 6 w | 3–9 w |
| DC Runner (remontée) | Nettoyer le rotor et la chambre de pompe | 4 | 2–6 |
| DC Runner (remontée) | Remplacer le rotor et les roulements | 18 | 12–24 |
| DC Runner (écumeur) | Nettoyer le gobelet | 2 w | 1–4 w |
| DC Runner (écumeur) | Nettoyer le venturi et le tuyau d'air | 4 w | 2–8 w |
| DC Runner (écumeur) | Nettoyer le rotor à aiguilles | 2 | 1–4 |
| DC Runner (écumeur) | Détartrer le corps de l'écumeur | 6 | 3–12 |
| DC Runner (écumeur) | Remplacer le rotor à aiguilles et les roulements | 18 | 12–24 |

> Valeurs en mois sauf si suivies de `w` (semaines). Aqua Medic ne publie aucun intervalle chiffré : ces valeurs viennent de la pratique récifale et sont toutes ajustables pompe par pompe.

### Notifications

L'intégration ne notifie jamais d'elle-même, volontairement. C'est le rôle du blueprint **Aqua Medic watch** livré avec le dépôt, qui couvre aussi les défauts matériels et les pompes hors ligne. Cliquez sur le bouton ci-dessous et confirmez l'import dans Home Assistant :

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-aquamedic-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faquamedic_alerts.en.yaml)

Une version française est disponible : [`aquamedic_alerts.fr.yaml`](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/blueprints/automation/aquamedic_alerts.fr.yaml).

Les tâches remontent aussi dans la vue maintenance de [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), à côté de celles de Red Sea : les deux intégrations publient le même contrat d'entités `reef_role`.

<!-- maintenance-section:end -->

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

## Développement

### Simulateur local

Un simulateur du cloud Gizwits (`scripts/gizwits_simulator.py`) permet de tester l'intégration sans matériel réel ni accès au cloud. Il se configure via `scripts/gizwits_sim_config.json` :

| Clé | Description |
|---|---|
| `username` / `password` | Identifiants que l'intégration doit utiliser pour se connecter |
| `virtual_ip` | IP sur laquelle le simulateur écoute (`127.0.0.1` ignore la configuration d'IP virtuelle) |
| `interface` | Interface réseau pour l'IP virtuelle (optionnel ; si omis, l'interface de la route par défaut est auto-détectée, avec repli sur `eth0` ; surchargeable avec `-i/--interface`) |
| `port` | Port d'écoute (défaut `8080`) |
| `devices` | Liste de `{ "type": ..., "count": N }` ; types disponibles : `smartdrift`, `dc_runner` (pompe de remontée), `dc_skimmer` |

Lancement : `sudo python3 scripts/gizwits_simulator.py` (root requis pour ajouter l'IP virtuelle).

Pour faire apparaître la région **Simulateur** dans le config flow, créez le fichier-drapeau local (git-ignoré, ne jamais le commiter) :

```bash
cp custom_components/aquamedic/simulator_enabled.example custom_components/aquamedic/.simulator_enabled
```

Redémarrez Home Assistant, ajoutez l'intégration et sélectionnez *Simulateur* ; l'URL du simulateur (défaut `http://localhost:8080`) et les identifiants du fichier de config vous seront alors demandés.

---

## Licence

MIT – voir [LICENSE](../../LICENSE).

