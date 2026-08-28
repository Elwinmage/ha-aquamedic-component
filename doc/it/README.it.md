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

<!-- ecosystem:start -->

## Progetti correlati

I progetti ReefTech si incastrano tra loro: le integrazioni portano la tua attrezzatura in Home Assistant, la scheda la mostra e la pilota, e il backup la mantiene in funzione durante un blackout. Ognuno funziona anche da solo.

<table>
  <tr>
    <th width="100px"></th>
    <th>Progetto</th>
    <th>Ruolo</th>
    <th>Funziona con</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="100" alt="ha-reefbeat-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reefbeat-component"><b>ha-reefbeat-component</b></a></td>
    <td>Dispositivi Red Sea ReefBeat, pilotati in locale senza cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave.<br />Include <b>ReefBeat watch</b>, un blueprint di allerta per manutenzioni scadute, modalità anomale, batteria scarica e dispositivi irraggiungibili. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="100" alt="ha-aquamedic-component" /></td>
    <td><b>ha-aquamedic-component</b><br /><i>(questo repository)</i></td>
    <td>Pompe Aqua Medic tramite l'API cloud Gizwits: pompe di movimento EcoDrift e SmartDrift, pompe DC Runner di risalita e dello schiumatoio.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="100" alt="ha-reef-maintenance-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Tracciamento di pulizia e usura per l'attrezzatura che Home Assistant non può interrogare: pompe di movimento, pompe di risalita, schiumatoi, reattori, tutto ciò che curi a mano.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="100" alt="ha-reef-card" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Vista grafica interattiva di ogni dispositivo sulla tua dashboard, e unico modo per modificare le programmazioni avanzate. Legge le tre integrazioni tramite il contratto <code>reef_role</code> comune, senza configurazione lato scheda.</td>
    <td>tutte e tre le integrazioni</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="100" alt="reefbeatEnergyBackup" /></td>
    <td><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Backup a batteria in caso di blackout. Un pacco 24V LiFePO₄ gestito da un Raspberry Pi, con degrado progressivo della velocità delle pompe in base allo stato di carica.</td>
    <td>da solo, o insieme a ha-reefbeat-component</td>
  </tr>
</table>

Sono tutti documentati insieme sulla [pagina del progetto ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

## Dispositivi supportati

Il tuo dispositivo non è supportato? Contattami.

> ✅ Supportato &nbsp;|&nbsp; 🧪 Non testato (potrebbe funzionare) &nbsp;|&nbsp; ❌ Non ancora supportato

| Dispositivo | | Nome interno | Chiave prodotto | Stato |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (pompa di ritorno) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic DC Runner (pompa per schiumatoio) | <img alt="schiumatoio" src="doc/img/skimmer.png" width="200" /> | `DC_Runner` | `00276aa006684c05805c297f60058c3d` | ✅ |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Tutti questi dispositivi utilizzano la piattaforma IoT Gizwits (lo stesso backend dell'app ufficiale Aqua Medic). Il supporto per ulteriori dispositivi potrà essere aggiunto nelle versioni future.

---

## Installazione

### Tramite HACS

L'integrazione è ora ufficialmente in HACS. Basta cercare **Aqua Medic** nella scheda Integrazioni e installare.

Oppure utilizza il pulsante di installazione diretta:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-aquamedic-component&category=integration)

Quindi riavviare Home Assistant.

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

### DC Runner (pompa di ritorno)

> 🧪 Il supporto è implementato ma **non ancora testato su hardware reale**. Feedback benvenuto.

#### Interruttori

| Entità | Descrizione |
|---|---|
| **Alimentazione** | Accensione/spegnimento principale |
| **Modalità alimentazione** | Mette in pausa il flusso per 10 minuti |
| **Modalità controllo 0-10V** | Quando attiva, disabilita il cursore di velocità (pompa controllata da segnale esterno 0-10V) |

#### Numeri

| Entità | Intervallo | Descrizione |
|---|---|---|
| **Portata** | 30–100 % | Velocità pompa (minimo 30 % — al di sotto il motore può bloccarsi) |

### DC Skimmer (pompa per schiumatoio DC Runner)

> ✅ Basato su una cattura reale dei datapoint del dispositivo.

#### Interruttori

| Entità | Descrizione |
|---|---|
| **Alimentazione** | Accensione/spegnimento principale |
| **Modalità alimentazione** | Attiva la pausa di alimentazione |
| **Timer** | Attiva il programma orario |
| **Modalità controllo 0-10V** | Quando attiva, disabilita il cursore di velocità (pompa controllata da segnale esterno 0-10V) |

#### Selezioni

| Entità | Opzioni |
|---|---|
| **Modalità programmata** | Arresto · Automatico · Alimentazione |

#### Numeri

| Entità | Intervallo | Descrizione |
|---|---|---|
| **Velocità del motore** | 30–100 % | Velocità pompa (minimo 30 % — al di sotto il motore può bloccarsi; disabilitata in modalità 0-10V) |
| **Durata alimentazione** | 1–60 min | Durata della pausa di alimentazione |
| **Velocità programmata** | 0–100 % | Velocità usata dal programma orario |
| **Durata alimentazione programmata** | 1–60 min | Durata di alimentazione usata dal programma orario |

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

> **Informazioni sul controllo 0-10V:** ogni controller DC Runner ha un ingresso fisico 0-10V per un controller per acquario esterno (Apex, GHL, …). È una porta hardware, non un valore cloud, quindi non appare come attributo del dispositivo — l'interruttore *Modalità controllo 0-10V* è un flag locale di Home Assistant che disabilita il cursore di velocità mentre la pompa è controllata esternamente. Secondo il manuale Aqua Medic, in modalità 0-10V la pompa deve funzionare al **≥ 60 %**.

---

<!-- maintenance-section:start -->

## Manutenzione

L'integrazione tiene traccia delle attività di pulizia e usura di ogni pompa. Ogni attività espone tre entità: un **pulsante** per registrare che è fatta, un **cursore** per regolare l'intervallo e un **interruttore** per silenziarne gli avvisi. Nulla viene inviato al cloud: lo stato è salvato in locale, per voce di configurazione.

La pompa di risalita DC Runner e la pompa dello schiumatoio condividono firmware e product key Gizwits, quindi l'API non può distinguerle. Dichiaralo una volta con il selettore **Ruolo della pompa**: l'elenco delle attività si adegua (l'integrazione si ricarica per applicarlo). Finché il ruolo è *Non definito*, una DC Runner non ha alcuna attività. Le EcoDrift / SmartDrift non lo chiedono mai.

| Pompa | Attività | Predefinito | Intervallo |
|---|---|---|---|
| EcoDrift / SmartDrift | Pulire il rotore e il cestello filtrante | 2 | 1–3 |
| EcoDrift / SmartDrift | Decalcificare la pompa | 6 | 3–9 |
| EcoDrift / SmartDrift | Sostituire il rotore e i cuscinetti | 18 | 12–24 |
| DC Runner (risalita) | Pulire il cestello di aspirazione | 6 w | 3–9 w |
| DC Runner (risalita) | Pulire il rotore e la camera della pompa | 4 | 2–6 |
| DC Runner (risalita) | Sostituire il rotore e i cuscinetti | 18 | 12–24 |
| DC Runner (schiumatoio) | Pulire il bicchiere di raccolta | 2 w | 1–4 w |
| DC Runner (schiumatoio) | Pulire il venturi e il tubo dell'aria | 4 w | 2–8 w |
| DC Runner (schiumatoio) | Pulire la girante ad aghi | 2 | 1–4 |
| DC Runner (schiumatoio) | Decalcificare il corpo dello schiumatoio | 6 | 3–12 |
| DC Runner (schiumatoio) | Sostituire la girante ad aghi e i cuscinetti | 18 | 12–24 |

> Valori in mesi salvo se seguiti da `w` (settimane). Aqua Medic non pubblica alcun intervallo numerico: questi valori derivano dalla pratica in acquario di barriera e sono regolabili pompa per pompa.

### Notifiche

L'integrazione non notifica mai da sola, di proposito. Se ne occupa il blueprint **Aqua Medic watch** incluso nel repository, che copre anche i guasti hardware e le pompe offline. Clicca il pulsante qui sotto e conferma l'importazione in Home Assistant:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-aquamedic-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faquamedic_alerts.en.yaml)

È disponibile una versione francese: [`aquamedic_alerts.fr.yaml`](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/blueprints/automation/aquamedic_alerts.fr.yaml).

Le attività compaiono anche nella vista manutenzione di [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), accanto a quelle Red Sea: entrambe le integrazioni pubblicano lo stesso contratto di entità `reef_role`.

<!-- maintenance-section:end -->

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

## Sviluppo

### Simulatore locale

Un simulatore del cloud Gizwits (`scripts/gizwits_simulator.py`) consente di testare l'integrazione senza hardware reale né accesso al cloud. Si configura tramite `scripts/gizwits_sim_config.json`:

| Chiave | Descrizione |
|---|---|
| `username` / `password` | Credenziali che l'integrazione deve usare |
| `virtual_ip` | IP a cui il simulatore si lega (`127.0.0.1` salta l'IP virtuale) |
| `interface` | Interfaccia di rete per l'IP virtuale (opzionale; se omessa viene rilevata automaticamente l'interfaccia della rotta predefinita, con fallback `eth0`; sovrascrivibile con `-i/--interface`) |
| `port` | Porta (predefinita `8080`) |
| `devices` | Elenco di `{ "type": ..., "count": N }`; tipi: `smartdrift`, `dc_runner` (pompa di ritorno), `dc_skimmer` |

Avvio: `sudo python3 scripts/gizwits_simulator.py` (root necessario per aggiungere l'IP virtuale).

Per far apparire la regione **Simulatore** nel flusso di configurazione, crea il file flag locale (ignorato da git, non committarlo mai):

```bash
cp custom_components/aquamedic/simulator_enabled.example custom_components/aquamedic/.simulator_enabled
```

Riavvia Home Assistant, aggiungi l'integrazione e seleziona *Simulatore*; verranno richiesti l'URL del simulatore (predefinito `http://localhost:8080`) e le credenziali.

---

## Licenza

MIT – vedere [LICENSE](../../LICENSE).

