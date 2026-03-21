# Aquamedic

<p align="center">
  <img src="icon.png"  width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/hacs)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Cloud%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-aquamedic-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-aquamedic-component/releases)
![Installations](https://img.shields.io/badge/dynamic/json?label=Active%20Installs&query=estimated&cacheSeconds=3600&url=https%3A%2F%2Fraw.githubusercontent.com%2FElwinmage%2Fha-aquamedic-component%2Fmain%2Fbadges%2Fstats.json&color=CE1126&logo=home-assistant)
[![Ruff Status](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-aquamedic-component)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-aquamedic-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-aquamedic-component)

# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/it/README.it.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/pt/README.pt.md)

Control your Aqua Medic pumps from Home Assistant via the Gizwits cloud API.

---

## Supported Devices

Your device is not supported? Please contact me.

> ✅ Supported &nbsp;|&nbsp; 🧪 Untested (may work) &nbsp;|&nbsp; ❌ Not yet supported

| Device | | Internal Name | Product Key | Status |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (return pump) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

All these devices use the Gizwits IoT platform (same backend as the official Aqua Medic app). Support for additional devices may be added in future releases.

---

## Installation

### Via HACS (recommended)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/Elwinmage/ha-aquamedic-component` as an **Integration**
3. Search for **Aqua Medic** and install
4. Restart Home Assistant

---

## Entities

### EcoDrift / SmartDrift

#### Switches

| Entity | Description |
|---|---|
| **Power** | Main on/off |
| **Wave type** | Pulse mode (off) / Tide mode (on) |
| **Feeding mode** | Activates feeding pause |
| **Timer** | Enables program mode |
| **0-10V control mode** | When on, disables the Flow rate slider (pump driven by external 0-10V signal) |

#### Selects

| Entity | Options |
|---|---|
| **Wave mode** | Classic wave · Sine wave · Random wave · Constant flow |
| **Linkage** | Independent · Master · Slave |

#### Numbers

| Entity | Range | Description |
|---|---|---|
| **Flow rate** | 0–100 % | Motor flow (disabled in 0-10V mode) |
| **Frequency** | 0–100 % | Wave frequency |
| **Feeding duration** | 1–60 min | Duration of feeding pause |

#### Binary Sensors (diagnostic)

| Entity | Description |
|---|---|
| **Overcurrent fault** | Motor overcurrent / short circuit |
| **Overvoltage fault** | Motor overvoltage |
| **Overtemperature fault** | Motor temperature too high |
| **Undervoltage fault** | Motor undervoltage |
| **Locked rotor fault** | Motor jammed / blocked |
| **No load fault** | Pump running dry |
| **UART communication fault** | Module ↔ mainboard communication error |

#### Button (diagnostic)

| Entity | Description |
|---|---|
| **Refresh** | Forces an immediate data refresh without waiting for the next poll interval |

### DC Runner

> 🧪 Support is implemented but **not yet tested on real hardware**. Feedback welcome.

#### Switches

| Entity | Description |
|---|---|
| **Power** | Main on/off |
| **Feeding mode** | Pauses pump output for 10 minutes |
| **0-10V control mode** | When on, flow is driven by external 0-10V signal |

#### Numbers

| Entity | Range | Description |
|---|---|---|
| **Flow rate** | 30–100 % | Pump speed (minimum 30 % — below this the motor may stall) |

#### Binary Sensors (diagnostic)

| Entity | Description |
|---|---|
| **Dry run fault** | Automatic shut-off if no water detected for 2 min |
| **Locked rotor fault** | Mechanical obstruction detected |
| **Voltage fault** | Input voltage out of range |

---

## Configuration

Go to **Settings → Devices & Services → Add Integration → Aqua Medic**.

| Field | Description |
|---|---|
| **E-mail** | Your Aqua Medic app account e-mail |
| **Password** | Your Aqua Medic app password |
| **Gizwits server** | Region server — select **Europe** for EU users |
| **Refresh interval** | How often device state is polled (5–300 s, default 30 s) |

The correct server is pre-selected automatically based on your Home Assistant language.

After setup, options (refresh interval) can be changed via **Settings → Devices & Services → Aqua Medic → Configure**.

---

## License

MIT – see [LICENSE](LICENSE).

***

[buymecoffee]: https://paypal.me/Elwinmage
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square
[ruff-shield]: https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/ruff.yml/badge.svg
[ruff-link]: https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/ruff.yml
[pyright-shield]: https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/pyright.yml/badge.svg
[pyright-link]: https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/pyright.yml
[coverage-shield]: https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/badges/coverage.svg
[coverage-link]: https://app.codecov.io/gh/Elwinmage/ha-aquamedic-component
