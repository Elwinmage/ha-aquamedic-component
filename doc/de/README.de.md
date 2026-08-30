# Aquamedic
> Teil des **[ReefTech Project Ökosystems](https://elwinmage.github.io/reeftank/de.html)**
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

Steuern Sie Ihre Aqua Medic Pumpen über die Gizwits-Cloud-API mit Home Assistant.

---

<!-- ecosystem:start -->

## Verwandte Projekte

Die ReefTech-Projekte greifen ineinander: die Integrationen bringen Ihre Geräte in Home Assistant, die Karte zeigt und steuert sie, und das Backup hält sie bei einem Stromausfall am Laufen. Jedes funktioniert auch für sich allein.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projekt</th>
    <th>Funktion</th>
    <th>Arbeitet mit</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reefbeat-component"><b>ha-reefbeat-component</b></a></td>
    <td>Red Sea ReefBeat-Geräte, lokal gesteuert ohne Cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun und ReefWave.<br />Enthält <b>ReefBeat watch</b>, ein Alarm-Blueprint für überfällige Wartungen, abweichende Modi, niedrigen Akkustand und nicht erreichbare Geräte. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td><b>ha-aquamedic-component</b><br /><i>(dieses Repository)</i></td>
    <td>Aqua Medic-Pumpen über die Gizwits-Cloud-API: EcoDrift- und SmartDrift-Strömungspumpen, DC Runner Rückförder- und Abschäumerpumpen.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Reinigungs- und Verschleißverfolgung für Geräte, die Home Assistant nicht erreicht: Strömungspumpen, Rückförderpumpen, Abschäumer, Reaktoren, alles was von Hand gewartet wird.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Interaktive grafische Ansicht jedes Geräts auf Ihrem Dashboard und der einzige Weg, erweiterte Zeitpläne zu bearbeiten. Liest die drei Integrationen über den gemeinsamen <code>reef_role</code>-Vertrag, ohne Konfiguration auf Kartenseite.</td>
    <td>alle drei Integrationen</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Batterie-Backup bei Stromausfall. Ein 24V LiFePO₄-Pack, gesteuert von einem Raspberry Pi, mit schrittweiser Reduzierung der Pumpendrehzahl je nach Ladezustand.</td>
    <td>eigenständig oder zusammen mit ha-reefbeat-component</td>
  </tr>
</table>

Alle zusammen sind auf der [ReefTech-Projektseite](https://elwinmage.github.io/reeftank/) dokumentiert.

<!-- ecosystem:end -->

## Unterstützte Geräte

Ihr Gerät wird nicht unterstützt? Kontaktieren Sie mich.

> ✅ Unterstützt &nbsp;|&nbsp; 🧪 Ungetestet (könnte funktionieren) &nbsp;|&nbsp; ❌ Noch nicht unterstützt

| Gerät | | Interner Name | Produktschlüssel | Status |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (Rückförderpumpe) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic DC Runner (Abschäumerpumpe) | <img alt="Abschäumer" src="doc/img/skimmer.png" width="200" /> | `DC_Runner` | `00276aa006684c05805c297f60058c3d` | ✅ |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Alle diese Geräte verwenden die Gizwits-IoT-Plattform (dasselbe Backend wie die offizielle Aqua Medic App). Die Unterstützung weiterer Geräte kann in zukünftigen Versionen hinzugefügt werden.

---

## Installation

### Via HACS

Die Integration ist jetzt offiziell in HACS. Suchen Sie einfach **Aqua Medic** in der Registerkarte Integrationen und installieren Sie es.

Oder verwenden Sie die direkte Installationsschaltfläche:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-aquamedic-component&category=integration)

Starten Sie dann Home Assistant neu.

---

## Entitäten

### EcoDrift / SmartDrift

#### Schalter

| Entität | Beschreibung |
|---|---|
| **Ein/Aus** | Hauptschalter |
| **Wellentyp** | Impulsmodus (aus) / Gezeitenmodus (ein) |
| **Fütterungsmodus** | Aktiviert die Fütterungspause |
| **Timer** | Aktiviert den Programmmodus |
| **0-10V-Steuermodus** | Wenn aktiv, wird der Durchflussregler deaktiviert |

#### Auswahllisten

| Entität | Optionen |
|---|---|
| **Wellenmodus** | Klassische Welle · Sinuswelle · Zufallswelle · Konstantfluss |
| **Kopplung** | Unabhängig · Master · Slave |

#### Zahlenwerte

| Entität | Bereich | Beschreibung |
|---|---|---|
| **Durchfluss** | 0–100 % | Motordurchfluss (im 0-10V-Modus deaktiviert) |
| **Frequenz** | 0–100 % | Wellenfrequenz |
| **Fütterungsdauer** | 1–60 Min. | Dauer der Fütterungspause |

#### Binärsensoren (Diagnose)

| Entität | Beschreibung |
|---|---|
| **Überstromfehler** | Motorüberstrom / Kurzschluss |
| **Überspannungsfehler** | Motorüberspannung |
| **Übertemperaturfehler** | Motortemperatur zu hoch |
| **Unterspannungsfehler** | Motorunterspannung |
| **Blockierter Rotor** | Motor blockiert / klemmt |
| **Leerlauf-Fehler** | Pumpe läuft trocken |
| **UART-Kommunikationsfehler** | Kommunikationsfehler Modul ↔ Hauptplatine |

#### Schaltfläche (Diagnose)

| Entität | Beschreibung |
|---|---|
| **Aktualisieren** | Erzwingt eine sofortige Aktualisierung |

### DC Runner (Rückförderpumpe)

> 🧪 Unterstützung ist implementiert, aber **noch nicht auf echter Hardware getestet**. Feedback willkommen.

#### Schalter

| Entität | Beschreibung |
|---|---|
| **Ein/Aus** | Hauptschalter |
| **Fütterungsmodus** | Unterbricht den Durchfluss für 10 Minuten |
| **0-10V-Steuermodus** | Wenn aktiv, wird der Geschwindigkeitsregler deaktiviert (Pumpe über externes 0-10V-Signal gesteuert) |

#### Zahlenwerte

| Entität | Bereich | Beschreibung |
|---|---|---|
| **Durchfluss** | 30–100 % | Pumpengeschwindigkeit (Minimum 30 % — darunter kann der Motor blockieren) |

### DC Skimmer (DC-Runner-Abschäumerpumpe)

> ✅ Basiert auf einer echten Datapoint-Aufnahme des Geräts.

#### Schalter

| Entität | Beschreibung |
|---|---|
| **Ein/Aus** | Hauptschalter |
| **Fütterungsmodus** | Aktiviert die Fütterungspause |
| **Timer** | Aktiviert das Zeitprogramm |
| **0-10V-Steuermodus** | Wenn aktiv, wird der Geschwindigkeitsregler deaktiviert (Pumpe über externes 0-10V-Signal gesteuert) |

#### Auswahllisten

| Entität | Optionen |
|---|---|
| **Zeitmodus** | Stopp · Automatik · Fütterung |

#### Zahlenwerte

| Entität | Bereich | Beschreibung |
|---|---|---|
| **Motordrehzahl** | 30–100 % | Pumpengeschwindigkeit (Minimum 30 % — darunter kann der Motor blockieren; im 0-10V-Modus deaktiviert) |
| **Fütterungsdauer** | 1–60 Min. | Dauer der Fütterungspause |
| **Timer-Drehzahl** | 0–100 % | Im Zeitprogramm verwendete Drehzahl |
| **Timer-Fütterungsdauer** | 1–60 Min. | Im Zeitprogramm verwendete Fütterungsdauer |

#### Binärsensoren (Diagnose)

| Entität | Beschreibung |
|---|---|
| **Überstromfehler** | Motorüberstrom / Kurzschluss |
| **Überspannungsfehler** | Motorüberspannung |
| **Übertemperaturfehler** | Motortemperatur zu hoch |
| **Unterspannungsfehler** | Motorunterspannung |
| **Blockierter Rotor** | Motor blockiert / klemmt |
| **Leerlauf-Fehler** | Pumpe läuft trocken |
| **UART-Kommunikationsfehler** | Kommunikationsfehler Modul ↔ Hauptplatine |

#### Schaltfläche (Diagnose)

| Entität | Beschreibung |
|---|---|
| **Aktualisieren** | Erzwingt eine sofortige Aktualisierung |

> **Zum 0-10V-Steuermodus:** Jeder DC-Runner-Controller besitzt einen physischen 0-10V-Eingang für einen externen Aquariencomputer (Apex, GHL, …). Es ist ein Hardware-Anschluss, kein Cloud-Wert, und erscheint daher nicht als Geräteattribut — der Schalter *0-10V-Steuermodus* ist ein lokales Home-Assistant-Flag, das den Geschwindigkeitsregler deaktiviert, während die Pumpe extern gesteuert wird. Laut Aqua-Medic-Handbuch muss die Pumpe im 0-10V-Modus mit **≥ 60 %** laufen.

---

<!-- maintenance-section:start -->

## Wartung

Die Integration verfolgt die Reinigungs- und Verschleißaufgaben jeder Pumpe. Jede Aufgabe hat drei Entitäten: einen **Button**, um die Erledigung zu erfassen, einen **Schieberegler** für das Intervall und einen **Schalter**, um ihre Meldungen stummzuschalten. Nichts wird in die Cloud gesendet — der Zustand wird lokal je Konfigurationseintrag gespeichert.

Die DC-Runner-Rückförderpumpe und die DC-Skimmer-Pumpe teilen sich Firmware und Gizwits-Product-Key, die API kann sie also nicht unterscheiden. Legen Sie es einmal über die Auswahl **Pumpenrolle** fest, die Aufgabenliste folgt (die Integration lädt sich dafür neu). Solange die Rolle *Nicht festgelegt* ist, hat eine DC Runner keine Aufgabe. EcoDrift / SmartDrift fragen nie.

| Pumpe | Aufgabe | Standard | Bereich |
|---|---|---|---|
| EcoDrift / SmartDrift | Rotor und Filterkorb reinigen | 2 | 1–3 |
| EcoDrift / SmartDrift | Pumpe entkalken | 6 | 3–9 |
| EcoDrift / SmartDrift | Rotor und Lager ersetzen | 18 | 12–24 |
| DC Runner (Rückförderung) | Ansaugkorb reinigen | 6 w | 3–9 w |
| DC Runner (Rückförderung) | Rotor und Pumpenkammer reinigen | 4 | 2–6 |
| DC Runner (Rückförderung) | Rotor und Lager ersetzen | 18 | 12–24 |
| DC Runner (Abschäumer) | Schaumtopf reinigen | 2 w | 1–4 w |
| DC Runner (Abschäumer) | Venturi und Luftschlauch reinigen | 4 w | 2–8 w |
| DC Runner (Abschäumer) | Nadelrad reinigen | 2 | 1–4 |
| DC Runner (Abschäumer) | Abschäumerkörper entkalken | 6 | 3–12 |
| DC Runner (Abschäumer) | Nadelrad und Lager ersetzen | 18 | 12–24 |

> Werte in Monaten, außer mit `w` (Wochen). Aqua Medic nennt keine Zahlenwerte; diese Vorgaben stammen aus der Riffaquaristik-Praxis und sind alle pro Pumpe einstellbar.

### Benachrichtigungen

Die Integration benachrichtigt absichtlich nie selbst. Das übernimmt der mitgelieferte Blueprint **Aqua Medic watch**, der auch Hardwarefehler und Offline-Pumpen abdeckt. Klicken Sie auf die Schaltfläche unten und bestätigen Sie den Import in Home Assistant:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-aquamedic-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faquamedic_alerts.en.yaml)

Eine französische Fassung liegt als [`aquamedic_alerts.fr.yaml`](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/blueprints/automation/aquamedic_alerts.fr.yaml) bei.

Die Aufgaben erscheinen auch in der Wartungsansicht von [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), neben denen von Red Sea: beide Integrationen veröffentlichen denselben `reef_role`-Entitätsvertrag.

<!-- maintenance-section:end -->

## Konfiguration

Gehen Sie zu **Einstellungen → Geräte & Dienste → Integration hinzufügen → Aqua Medic**.

| Feld | Beschreibung |
|---|---|
| **E-Mail** | E-Mail-Adresse Ihres Aqua Medic-Kontos |
| **Passwort** | Passwort Ihres Aqua Medic-Kontos |
| **Gizwits-Server** | Regionaler Server — **Europa** für EU-Nutzer wählen |
| **Aktualisierungsintervall** | Abfrageintervall (5–300 s, Standard 30 s) |

Der richtige Server wird automatisch anhand der Home Assistant-Sprache vorausgewählt.

Nach der Einrichtung kann das Aktualisierungsintervall über **Einstellungen → Geräte & Dienste → Aqua Medic → Konfigurieren** geändert werden.

---

## Entwicklung

### Lokaler Simulator

Ein Gizwits-Cloud-Simulator (`scripts/gizwits_simulator.py`) ermöglicht das Testen der Integration ohne echte Hardware oder Cloud-Zugang. Konfiguration über `scripts/gizwits_sim_config.json`:

| Schlüssel | Beschreibung |
|---|---|
| `username` / `password` | Anmeldedaten, die die Integration verwenden muss |
| `virtual_ip` | IP, an die der Simulator bindet (`127.0.0.1` überspringt die virtuelle IP) |
| `interface` | Netzwerkschnittstelle für die virtuelle IP (optional; wird sonst automatisch über die Standardroute erkannt, Fallback `eth0`; überschreibbar mit `-i/--interface`) |
| `port` | Port (Standard `8080`) |
| `devices` | Liste von `{ "type": ..., "count": N }`; Typen: `smartdrift`, `dc_runner` (Rückförderpumpe), `dc_skimmer` |

Start: `sudo python3 scripts/gizwits_simulator.py` (Root nötig für die virtuelle IP).

Damit die Region **Simulator** im Konfigurationsdialog erscheint, lege die lokale Flag-Datei an (git-ignoriert, niemals committen):

```bash
cp custom_components/aquamedic/simulator_enabled.example custom_components/aquamedic/.simulator_enabled
```

Starte Home Assistant neu, füge die Integration hinzu und wähle *Simulator*; danach werden die Simulator-URL (Standard `http://localhost:8080`) und die Zugangsdaten abgefragt.

---

## Lizenz

MIT – siehe [LICENSE](../../LICENSE).

