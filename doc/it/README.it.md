# Aquamedic
> Fa parte dell'**[Ecosistema ReefTech Project](https://elwinmage.github.io/reeftank/it.html)**
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

Controlla le tue pompe Aqua Medic da Home Assistant tramite l'API cloud Gizwits.

---

## Dispositivi supportati

Il tuo dispositivo non è supportato? Contattami.

> ✅ Supportato &nbsp;|&nbsp; 🧪 Non testato (potrebbe funzionare) &nbsp;|&nbsp; ❌ Non ancora supportato

| Dispositivo | | Nome interno | Chiave prodotto | Stato |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (pompa di ritorno) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Tutti questi dispositivi utilizzano la piattaforma IoT Gizwits (lo stesso backend dell'app ufficiale Aqua Medic). Il supporto per ulteriori dispositivi potrà essere aggiunto nelle versioni future.

---

## Installazione

### Tramite HACS (consigliato)

1. In HACS, andare su **Integrazioni → ⋮ → Repository personalizzati**
2. Aggiungere `https://github.com/Elwinmage/ha-aquamedic-component` come **Integrazione**
3. Cercare **Aqua Medic** e installare
4. Riavviare Home Assistant

---

## Entità

### EcoDrift / SmartDrift

#### Interruttori

| Entità | Descrizione |
|---|---|
| **Alimentazione** | Accensione/spegnimento principale |
| **Tipo di onda** | Modalità impulso (spento) / Modalità marea (acceso) |
| **Modalità alimentazione** | Attiva la pausa di alimentazione |
| **Timer** | Attiva la modalità programmata |
| **Modalità controllo 0-10V** | Quando attiva, disabilita il cursore di portata |

#### Selezioni

| Entità | Opzioni |
|---|---|
| **Modalità onda** | Onda classica · Onda sinusoidale · Onda casuale · Flusso costante |
| **Collegamento** | Indipendente · Master · Slave |

#### Numeri

| Entità | Intervallo | Descrizione |
|---|---|---|
| **Portata** | 0–100 % | Portata motore (disabilitata in modalità 0-10V) |
| **Frequenza** | 0–100 % | Frequenza delle onde |
| **Durata alimentazione** | 1–60 min | Durata della pausa di alimentazione |

#### Sensori binari (diagnostica)

| Entità | Descrizione |
|---|---|
| **Guasto sovracorrente** | Sovracorrente / cortocircuito motore |
| **Guasto sovratensione** | Sovratensione motore |
| **Guasto sovratemperatura** | Temperatura motore troppo alta |
| **Guasto sottotensione** | Sottotensione motore |
| **Guasto rotore bloccato** | Motore inceppato / bloccato |
| **Guasto senza carico** | Pompa in funzionamento a secco |
| **Guasto comunicazione UART** | Errore di comunicazione modulo ↔ scheda principale |

#### Pulsante (diagnostica)

| Entità | Descrizione |
|---|---|
| **Aggiorna** | Forza un aggiornamento immediato |

### DC Runner

> 🧪 Il supporto è implementato ma **non ancora testato su hardware reale**. Feedback benvenuto.

#### Interruttori

| Entità | Descrizione |
|---|---|
| **Alimentazione** | Accensione/spegnimento principale |
| **Modalità alimentazione** | Mette in pausa il flusso per 10 minuti |
| **Modalità controllo 0-10V** | Quando attiva, il flusso è controllato da segnale esterno 0-10V |

#### Numeri

| Entità | Intervallo | Descrizione |
|---|---|---|
| **Portata** | 30–100 % | Velocità pompa (minimo 30 % — al di sotto il motore può bloccarsi) |

#### Sensori binari (diagnostica)

| Entità | Descrizione |
|---|---|
| **Guasto marcia a secco** | Spegnimento automatico se nessuna acqua rilevata per 2 min |
| **Guasto rotore bloccato** | Ostacolo meccanico rilevato |
| **Guasto tensione** | Tensione di alimentazione fuori range |

---

## Configurazione

Andare su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Aqua Medic**.

| Campo | Descrizione |
|---|---|
| **E-mail** | Indirizzo e-mail account Aqua Medic |
| **Password** | Password account Aqua Medic |
| **Server Gizwits** | Server regionale — **Europa** per gli utenti EU |
| **Intervallo di aggiornamento** | Frequenza di polling (5–300 s, predefinito 30 s) |

Il server corretto viene preselezionato automaticamente in base alla lingua di Home Assistant.

Dopo la configurazione, l'intervallo può essere modificato tramite **Impostazioni → Dispositivi e servizi → Aqua Medic → Configura**.

---

## Licenza

MIT – vedere [LICENSE](../../LICENSE).

