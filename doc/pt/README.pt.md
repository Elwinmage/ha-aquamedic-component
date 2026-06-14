# Aquamedic
> Parte do **[Ecossistema ReefTech Project](https://elwinmage.github.io/reeftank/pt.html)**
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

Controle suas bombas Aqua Medic a partir do Home Assistant através da API cloud Gizwits.

---

## Dispositivos suportados

O seu dispositivo não é suportado? Entre em contato comigo.

> ✅ Suportado &nbsp;|&nbsp; 🧪 Não testado (pode funcionar) &nbsp;|&nbsp; ❌ Ainda não suportado

| Dispositivo | | Nome interno | Chave do produto | Estado |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (bomba de retorno) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic DC Runner (bomba de escumador) | | `DC_Runner` | `00276aa006684c05805c297f60058c3d` | ✅ |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Todos estes dispositivos utilizam a plataforma IoT Gizwits (o mesmo backend que a aplicação oficial Aqua Medic). O suporte a dispositivos adicionais podrá ser adicionado em versões futuras.

---

## Instalação

### Via HACS (recomendado)

1. No HACS, ir a **Integrações → ⋮ → Repositórios personalizados**
2. Adicionar `https://github.com/Elwinmage/ha-aquamedic-component` como **Integração**
3. Procurar **Aqua Medic** e instalar
4. Reiniciar o Home Assistant

---

## Entidades

### EcoDrift / SmartDrift

#### Interruptores

| Entidade | Descrição |
|---|---|
| **Alimentação** | Ligar/desligar principal |
| **Tipo de onda** | Modo impulso (desligado) / Modo maré (ligado) |
| **Modo alimentação** | Ativa a pausa de alimentação |
| **Temporizador** | Ativa o modo de programa |
| **Modo controlo 0-10V** | Quando ativo, desativa o controlo de caudal |

#### Seletores

| Entidade | Opções |
|---|---|
| **Modo de onda** | Onda clássica · Onda sinusoidal · Onda aleatória · Fluxo constante |
| **Ligação** | Independente · Mestre · Escravo |

#### Números

| Entidade | Intervalo | Descrição |
|---|---|---|
| **Caudal** | 0–100 % | Caudal do motor (desativado no modo 0-10V) |
| **Frequência** | 0–100 % | Frequência das ondas |
| **Duração da alimentação** | 1–60 min | Duração da pausa de alimentação |

#### Sensores binários (diagnóstico)

| Entidade | Descrição |
|---|---|
| **Falha de sobrecorrente** | Sobrecorrente / curto-circuito do motor |
| **Falha de sobretensão** | Sobretensão do motor |
| **Falha de sobretemperatura** | Temperatura do motor demasiado alta |
| **Falha de subtensão** | Subtensão do motor |
| **Falha de rotor bloqueado** | Motor encravado / bloqueado |
| **Falha sem carga** | Bomba a funcionar em seco |
| **Falha de comunicação UART** | Erro de comunicação módulo ↔ placa principal |

#### Botão (diagnóstico)

| Entidade | Descrição |
|---|---|
| **Atualizar** | Força uma atualização imediata |

### DC Runner (bomba de retorno)

> 🧪 O suporte está implementado mas **ainda não testado em hardware real**. Feedback bem-vindo.

#### Interruptores

| Entidade | Descrição |
|---|---|
| **Alimentação** | Ligar/desligar principal |
| **Modo alimentação** | Pausa o caudal durante 10 minutos |
| **Modo controlo 0-10V** | Quando ativo, desativa o controlo de velocidade (bomba controlada por sinal externo 0-10V) |

#### Números

| Entidade | Intervalo | Descrição |
|---|---|---|
| **Caudal** | 30–100 % | Velocidade da bomba (mínimo 30 % — abaixo disso o motor pode bloquear) |

### DC Skimmer (bomba de escumador DC Runner)

> ✅ Baseado numa captura real dos datapoints do dispositivo.

#### Interruptores

| Entidade | Descrição |
|---|---|
| **Alimentação** | Ligar/desligar principal |
| **Modo alimentação** | Ativa a pausa de alimentação |
| **Temporizador** | Ativa o programa horário |
| **Modo controlo 0-10V** | Quando ativo, desativa o controlo de velocidade (bomba controlada por sinal externo 0-10V) |

#### Seletores

| Entidade | Opções |
|---|---|
| **Modo programado** | Parar · Automático · Alimentação |

#### Números

| Entidade | Intervalo | Descrição |
|---|---|---|
| **Velocidade do motor** | 30–100 % | Velocidade da bomba (mínimo 30 % — abaixo disso o motor pode bloquear; desativado no modo 0-10V) |
| **Duração da alimentação** | 1–60 min | Duração da pausa de alimentação |
| **Velocidade programada** | 0–100 % | Velocidade usada pelo programa horário |
| **Duração da alimentação programada** | 1–60 min | Duração de alimentação usada pelo programa horário |

#### Sensores binários (diagnóstico)

| Entidade | Descrição |
|---|---|
| **Falha de sobrecorrente** | Sobrecorrente / curto-circuito do motor |
| **Falha de sobretensão** | Sobretensão do motor |
| **Falha de sobretemperatura** | Temperatura do motor demasiado alta |
| **Falha de subtensão** | Subtensão do motor |
| **Falha de rotor bloqueado** | Motor encravado / bloqueado |
| **Falha sem carga** | Bomba a funcionar em seco |
| **Falha de comunicação UART** | Erro de comunicação módulo ↔ placa principal |

#### Botão (diagnóstico)

| Entidade | Descrição |
|---|---|
| **Atualizar** | Força uma atualização imediata |

> **Sobre o controlo 0-10V:** cada controlador DC Runner tem uma entrada física 0-10V para um controlador de aquário externo (Apex, GHL, …). É uma porta de hardware, não um valor na nuvem, pelo que não aparece como atributo do dispositivo — o interruptor *Modo controlo 0-10V* é um sinalizador local do Home Assistant que desativa o controlo de velocidade enquanto a bomba é controlada externamente. De acordo com o manual da Aqua Medic, no modo 0-10V a bomba deve funcionar a **≥ 60 %**.

---

## Configuração

Ir a **Definições → Dispositivos e serviços → Adicionar integração → Aqua Medic**.

| Campo | Descrição |
|---|---|
| **E-mail** | Endereço de e-mail da conta Aqua Medic |
| **Palavra-passe** | Palavra-passe da conta Aqua Medic |
| **Servidor Gizwits** | Servidor regional — **Europa** para utilizadores da UE |
| **Intervalo de atualização** | Frequência de polling (5–300 s, predefinição 30 s) |

O servidor correto é pré-selecionado automaticamente com base no idioma do Home Assistant.

Após a configuração, o intervalo pode ser alterado em **Definições → Dispositivos e serviços → Aqua Medic → Configurar**.

---

## Desenvolvimento

### Simulador local

Um simulador do cloud Gizwits (`scripts/gizwits_simulator.py`) permite testar a integração sem hardware real nem acesso ao cloud. Configura-se através de `scripts/gizwits_sim_config.json`:

| Chave | Descrição |
|---|---|
| `username` / `password` | Credenciais que a integração deve usar |
| `virtual_ip` | IP onde o simulador escuta (`127.0.0.1` ignora o IP virtual) |
| `interface` | Interface de rede para o IP virtual (opcional; se omitido, a interface da rota predefinida é detetada automaticamente, com `eth0` como recurso; substituível com `-i/--interface`) |
| `port` | Porta (predefinição `8080`) |
| `devices` | Lista de `{ "type": ..., "count": N }`; tipos: `smartdrift`, `dc_runner` (bomba de retorno), `dc_skimmer` |

Execução: `sudo python3 scripts/gizwits_simulator.py` (root necessário para adicionar o IP virtual).

Para que a região **Simulador** apareça no fluxo de configuração, crie o ficheiro de sinalização local (ignorado pelo git, nunca o submeta):

```bash
cp custom_components/aquamedic/simulator_enabled.example custom_components/aquamedic/.simulator_enabled
```

Reinicie o Home Assistant, adicione a integração e selecione *Simulador*; ser-lhe-á pedido o URL do simulador (predefinição `http://localhost:8080`) e as credenciais.

---

## Licença

MIT – ver [LICENSE](../../LICENSE).

