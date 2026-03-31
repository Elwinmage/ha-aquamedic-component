# Aquamedic
> Teil des **[ReefTech Project Ökosystems](https://elwinmage.github.io/reeftank/de.html)**
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

Steuern Sie Ihre Aqua Medic Pumpen über die Gizwits-Cloud-API mit Home Assistant.

---

## Unterstützte Geräte

Ihr Gerät wird nicht unterstützt? Kontaktieren Sie mich.

> ✅ Unterstützt &nbsp;|&nbsp; 🧪 Ungetestet (könnte funktionieren) &nbsp;|&nbsp; ❌ Noch nicht unterstützt

| Gerät | | Interner Name | Produktschlüssel | Status |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (Rückförderpumpe) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Alle diese Geräte verwenden die Gizwits-IoT-Plattform (dasselbe Backend wie die offizielle Aqua Medic App). Die Unterstützung weiterer Geräte kann in zukünftigen Versionen hinzugefügt werden.

---

## Installation

### Über HACS (empfohlen)

1. In HACS zu **Integrationen → ⋮ → Benutzerdefinierte Repositories** gehen
2. `https://github.com/Elwinmage/ha-aquamedic-component` als **Integration** hinzufügen
3. Nach **Aqua Medic** suchen und installieren
4. Home Assistant neu starten

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

### DC Runner

> 🧪 Unterstützung ist implementiert, aber **noch nicht auf echter Hardware getestet**. Feedback willkommen.

#### Schalter

| Entität | Beschreibung |
|---|---|
| **Ein/Aus** | Hauptschalter |
| **Fütterungsmodus** | Unterbricht den Durchfluss für 10 Minuten |
| **0-10V-Steuermodus** | Wenn aktiv, wird der Durchfluss durch externes 0-10V-Signal gesteuert |

#### Zahlenwerte

| Entität | Bereich | Beschreibung |
|---|---|---|
| **Durchfluss** | 30–100 % | Pumpengeschwindigkeit (Minimum 30 % — darunter kann der Motor blockieren) |

#### Binärsensoren (Diagnose)

| Entität | Beschreibung |
|---|---|
| **Trocklauf-Fehler** | Automatische Abschaltung wenn 2 Min. kein Wasser erkannt |
| **Blockierter Rotor** | Mechanische Blockierung erkannt |
| **Spannungsfehler** | Versorgungsspannung außerhalb des Bereichs |

---

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

## Lizenz

MIT – siehe [LICENSE](../../LICENSE).

