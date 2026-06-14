# Aquamedic
> Parte del **[Ecosistema ReefTech Project](https://elwinmage.github.io/reeftank/es.html)**
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

Controle sus bombas Aqua Medic desde Home Assistant a través de la API cloud de Gizwits.

---

## Dispositivos compatibles

¿Su dispositivo no es compatible? Contácteme.

> ✅ Compatible &nbsp;|&nbsp; 🧪 Sin probar (puede funcionar) &nbsp;|&nbsp; ❌ Aún no compatible

| Dispositivo | | Nombre interno | Clave de producto | Estado |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (bomba de retorno) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic DC Runner (bomba de espumador) | <img alt="espumador" src="doc/img/skimmer.png" width="200" /> | `DC_Runner` | `00276aa006684c05805c297f60058c3d` | ✅ |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Todos estos dispositivos utilizan la plataforma IoT Gizwits (el mismo backend que la aplicación oficial Aqua Medic). La compatibilidad con dispositivos adicionales podrá añadirse en futuras versiones.

---

## Instalación

### A través de HACS

La integración está ahora oficialmente en HACS. Simplemente busque **Aqua Medic** en la pestaña Integraciones e instale.

O use el botón de instalación directa:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-aquamedic-component&category=integration)

Luego reinicie Home Assistant.

---

## Entidades

### EcoDrift / SmartDrift

#### Interruptores

| Entidad | Descripción |
|---|---|
| **Encendido** | Encendido/apagado principal |
| **Tipo de ola** | Modo impulso (apagado) / Modo marea (encendido) |
| **Modo alimentación** | Activa la pausa de alimentación |
| **Temporizador** | Activa el modo de programa |
| **Modo control 0-10V** | Cuando está activo, desactiva el control de caudal |

#### Selectores

| Entidad | Opciones |
|---|---|
| **Modo de ola** | Ola clásica · Ola sinusoidal · Ola aleatoria · Flujo constante |
| **Enlace** | Independiente · Maestro · Esclavo |

#### Números

| Entidad | Rango | Descripción |
|---|---|---|
| **Caudal** | 0–100 % | Caudal del motor (desactivado en modo 0-10V) |
| **Frecuencia** | 0–100 % | Frecuencia de las olas |
| **Duración de alimentación** | 1–60 min | Duración de la pausa de alimentación |

#### Sensores binarios (diagnóstico)

| Entidad | Descripción |
|---|---|
| **Fallo de sobrecorriente** | Sobrecorriente / cortocircuito del motor |
| **Fallo de sobretensión** | Sobretensión del motor |
| **Fallo de sobretemperatura** | Temperatura del motor demasiado alta |
| **Fallo de subtensión** | Subtensión del motor |
| **Fallo de rotor bloqueado** | Motor atascado / bloqueado |
| **Fallo sin carga** | Bomba funcionando en seco |
| **Fallo de comunicación UART** | Error de comunicación módulo ↔ placa principal |

#### Botón (diagnóstico)

| Entidad | Descripción |
|---|---|
| **Actualizar** | Fuerza una actualización inmediata |

### DC Runner (bomba de retorno)

> 🧪 El soporte está implementado pero **aún no probado en hardware real**. Se agradecen comentarios.

#### Interruptores

| Entidad | Descripción |
|---|---|
| **Encendido** | Encendido/apagado principal |
| **Modo alimentación** | Detiene el caudal durante 10 minutos |
| **Modo control 0-10V** | Cuando está activo, desactiva el control de velocidad (bomba controlada por señal externa 0-10V) |

#### Números

| Entidad | Rango | Descripción |
|---|---|---|
| **Caudal** | 30–100 % | Velocidad de la bomba (mínimo 30 % — por debajo el motor puede bloquearse) |

### DC Skimmer (bomba de espumador DC Runner)

> ✅ Basado en una captura real de los datapoints del dispositivo.

#### Interruptores

| Entidad | Descripción |
|---|---|
| **Encendido** | Encendido/apagado principal |
| **Modo alimentación** | Activa la pausa de alimentación |
| **Temporizador** | Activa el programa horario |
| **Modo control 0-10V** | Cuando está activo, desactiva el control de velocidad (bomba controlada por señal externa 0-10V) |

#### Selectores

| Entidad | Opciones |
|---|---|
| **Modo programado** | Parada · Automático · Alimentación |

#### Números

| Entidad | Rango | Descripción |
|---|---|---|
| **Velocidad del motor** | 30–100 % | Velocidad de la bomba (mínimo 30 % — por debajo el motor puede bloquearse; desactivado en modo 0-10V) |
| **Duración de alimentación** | 1–60 min | Duración de la pausa de alimentación |
| **Velocidad programada** | 0–100 % | Velocidad usada por el programa horario |
| **Duración de alimentación programada** | 1–60 min | Duración de alimentación usada por el programa horario |

#### Sensores binarios (diagnóstico)

| Entidad | Descripción |
|---|---|
| **Fallo de sobrecorriente** | Sobrecorriente / cortocircuito del motor |
| **Fallo de sobretensión** | Sobretensión del motor |
| **Fallo de sobretemperatura** | Temperatura del motor demasiado alta |
| **Fallo de subtensión** | Subtensión del motor |
| **Fallo de rotor bloqueado** | Motor atascado / bloqueado |
| **Fallo sin carga** | Bomba funcionando en seco |
| **Fallo de comunicación UART** | Error de comunicación módulo ↔ placa principal |

#### Botón (diagnóstico)

| Entidad | Descripción |
|---|---|
| **Actualizar** | Fuerza una actualización inmediata |

> **Sobre el control 0-10V:** cada controlador DC Runner tiene una entrada física 0-10V para un controlador de acuario externo (Apex, GHL, …). Es un puerto de hardware, no un valor en la nube, por lo que no aparece como atributo del dispositivo — el interruptor *Modo control 0-10V* es un indicador local de Home Assistant que desactiva el control de velocidad mientras la bomba se controla externamente. Según el manual de Aqua Medic, en modo 0-10V la bomba debe funcionar al **≥ 60 %**.

---

## Configuración

Ir a **Configuración → Dispositivos y servicios → Añadir integración → Aqua Medic**.

| Campo | Descripción |
|---|---|
| **E-mail** | Correo de su cuenta Aqua Medic |
| **Contraseña** | Contraseña de su cuenta Aqua Medic |
| **Servidor Gizwits** | Servidor regional — **Europa** para usuarios de la UE |
| **Intervalo de actualización** | Frecuencia de sondeo (5–300 s, predeterminado 30 s) |

El servidor correcto se preselecciona automáticamente según el idioma de Home Assistant.

Tras la configuración, el intervalo puede modificarse en **Configuración → Dispositivos y servicios → Aqua Medic → Configurar**.

---

## Desarrollo

### Simulador local

Un simulador del cloud Gizwits (`scripts/gizwits_simulator.py`) permite probar la integración sin hardware real ni acceso al cloud. Se configura mediante `scripts/gizwits_sim_config.json`:

| Clave | Descripción |
|---|---|
| `username` / `password` | Credenciales que la integración debe usar |
| `virtual_ip` | IP a la que se enlaza el simulador (`127.0.0.1` omite la IP virtual) |
| `interface` | Interfaz de red para la IP virtual (opcional; si se omite, se autodetecta la interfaz de la ruta por defecto, con `eth0` como reserva; se puede forzar con `-i/--interface`) |
| `port` | Puerto (por defecto `8080`) |
| `devices` | Lista de `{ "type": ..., "count": N }`; tipos: `smartdrift`, `dc_runner` (bomba de retorno), `dc_skimmer` |

Ejecución: `sudo python3 scripts/gizwits_simulator.py` (se requiere root para añadir la IP virtual).

Para que la región **Simulador** aparezca en el flujo de configuración, crea el archivo indicador local (ignorado por git, nunca lo subas):

```bash
cp custom_components/aquamedic/simulator_enabled.example custom_components/aquamedic/.simulator_enabled
```

Reinicia Home Assistant, añade la integración y selecciona *Simulador*; se te pedirá la URL del simulador (por defecto `http://localhost:8080`) y las credenciales.

---

## Licencia

MIT – ver [LICENSE](../../LICENSE).

