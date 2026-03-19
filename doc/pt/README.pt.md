# Aquamedic

<p align="center">
  <img src="../../icon.png"  width="50%"/>
</p>

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/hacs)
[![IoT Class](https://img.shields.io/badge/IoT%20Class-Cloud%20Polling-green?style=flat-square)](https://developers.home-assistant.io/docs/architecture_index/#branding)
[![GH-release](https://img.shields.io/github/v/release/Elwinmage/ha-aquamedic-component.svg?style=flat-square)](https://github.com/Elwinmage/ha-aquamedic-component/releases)
[![Ruff Status](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/main.yml/badge.svg)](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/main.yml)
[![HA & HACS Validation](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/hass_and_hacs.yml/badge.svg)](https://github.com/Elwinmage/ha-aquamedic-component/actions/workflows/hass_and_hacs.yml)
[![Coverage](https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/badges/coverage.svg)](https://app.codecov.io/gh/Elwinmage/ha-aquamedic-component)
[![GH-code-size](https://img.shields.io/github/languages/code-size/Elwinmage/ha-aquamedic-component.svg?color=red&style=flat-square)](https://github.com/Elwinmage/ha-aquamedic-component)

# Supported Languages: [<img src="https://flagicons.lipis.dev/flags/4x3/gb.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/README.md) [<img src="https://flagicons.lipis.dev/flags/4x3/fr.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/fr/README.fr.md) [<img src="https://flagicons.lipis.dev/flags/4x3/de.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/de/README.de.md) [<img src="https://flagicons.lipis.dev/flags/4x3/es.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/es/README.es.md) [<img src="https://flagicons.lipis.dev/flags/4x3/it.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/it/README.it.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pl.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/pl/README.pl.md) [<img src="https://flagicons.lipis.dev/flags/4x3/pt.svg" width="5%"/>](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/doc/pt/README.pt.md)

Controle suas bombas de ondas Aqua Medic a partir do Home Assistant através da API cloud Gizwits.

---

## Dispositivos suportados

O seu dispositivo não é suportado? Entre em contato comigo.

| Dispositivo | Nome interno | Chave do produto | Suportado |
|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner (bomba de retorno) | `DC_Runner` | `8879684725d14066922374e50889f893` | ❌ |
| Aqua Medic Reefdoser EVO | `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Todos estes dispositivos utilizam a plataforma IoT Gizwits (mesmo backend que a aplicação oficial Aqua Medic). O suporte a dispositivos adicionais poderá ser adicionado em versões futuras.

---

## Entidades

Cada dispositivo SmartDrift / EcoDrift expõe as seguintes entidades no Home Assistant.

### Interruptores

| Entidade | Descrição |
|---|---|
| **Alimentação** | Ligar/desligar principal |
| **Tipo de onda** | Modo impulso (desligado) / Modo maré (ligado) |
| **Modo alimentação** | Ativa a pausa de alimentação |
| **Temporizador** | Ativa o modo de programa |
| **Modo controlo 0-10V** | Quando ativo, desativa o controlo de caudal (a bomba é controlada por sinal externo 0-10V) |

### Seletores

| Entidade | Opções |
|---|---|
| **Modo de onda** | Onda clássica · Onda sinusoidal · Onda aleatória · Fluxo constante |
| **Ligação** | Independente · Mestre · Escravo |

### Números

| Entidade | Intervalo | Descrição |
|---|---|---|
| **Caudal** | 0–100 % | Caudal do motor (desativado no modo 0-10V) |
| **Frequência** | 0–100 % | Frequência das ondas |
| **Duração da alimentação** | 1–60 min | Duração da pausa de alimentação |

### Sensores binários (diagnóstico)

| Entidade | Descrição |
|---|---|
| **Falha de sobrecorrente** | Sobrecorrente / curto-circuito do motor |
| **Falha de sobretensão** | Sobretensão do motor |
| **Falha de sobretemperatura** | Temperatura do motor demasiado alta |
| **Falha de subtensão** | Subtensão do motor |
| **Falha de rotor bloqueado** | Motor encravado / bloqueado |
| **Falha sem carga** | Bomba a funcionar em seco |
| **Falha de comunicação UART** | Erro de comunicação módulo ↔ placa principal |

### Botão (diagnóstico)

| Entidade | Descrição |
|---|---|
| **Atualizar** | Força uma atualização imediata sem aguardar o próximo ciclo de polling |

---

## Instalação

### Via HACS (recomendado)

1. No HACS, ir a **Integrações → ⋮ → Repositórios personalizados**
2. Adicionar `https://github.com/Elwinmage/ha-aquamedic-component` como **Integração**
3. Procurar **Aqua Medic** e instalar
4. Reiniciar o Home Assistant

---

## Configuração

Ir a **Definições → Dispositivos e serviços → Adicionar integração → Aqua Medic**.

| Campo | Descrição |
|---|---|
| **E-mail** | Endereço de e-mail da sua conta Aqua Medic |
| **Palavra-passe** | Palavra-passe da sua conta Aqua Medic |
| **Servidor Gizwits** | Servidor regional — selecionar **Europa** para utilizadores da UE |
| **Intervalo de atualização** | Frequência de polling do dispositivo (5–300 s, predefinição 30 s) |

O servidor correto é pré-selecionado automaticamente com base no idioma do Home Assistant.

Após a configuração, o intervalo de atualização pode ser alterado em **Definições → Dispositivos e serviços → Aqua Medic → Configurar**.

---

## Licença

MIT – ver [LICENSE](../../LICENSE).
