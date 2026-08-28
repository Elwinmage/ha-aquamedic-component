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

<!-- ecosystem:start -->

## Projetos relacionados

Os projetos ReefTech encaixam-se entre si: as integrações trazem o seu equipamento para o Home Assistant, o cartão mostra-o e comanda-o, e o backup mantém-no a funcionar durante um corte. Cada um funciona também sozinho.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projeto</th>
    <th>Função</th>
    <th>Funciona com</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="100" alt="ha-reefbeat-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reefbeat-component"><b>ha-reefbeat-component</b></a></td>
    <td>Aparelhos Red Sea ReefBeat, comandados localmente sem cloud: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun e ReefWave.<br />Inclui <b>ReefBeat watch</b>, um blueprint de alertas para manutenções em atraso, modos anómalos, bateria fraca e aparelhos inacessíveis. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="100" alt="ha-aquamedic-component" /></td>
    <td><b>ha-aquamedic-component</b><br /><i>(este repositório)</i></td>
    <td>Bombas Aqua Medic através da API cloud Gizwits: bombas de circulação EcoDrift e SmartDrift, bombas DC Runner de retorno e do escumador.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="100" alt="ha-reef-maintenance-component" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Acompanhamento da limpeza e do desgaste do equipamento que o Home Assistant não consegue interrogar: bombas de circulação, bombas de retorno, escumadores, reatores, tudo o que trata à mão.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="100" alt="ha-reef-card" /></td>
    <td><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Vista gráfica interativa de cada aparelho no seu painel, e a única forma de editar os programas avançados. Lê as três integrações através do contrato <code>reef_role</code> comum, sem configuração do lado do cartão.</td>
    <td>as três integrações</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="100" alt="reefbeatEnergyBackup" /></td>
    <td><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Backup por bateria em caso de corte. Um pack 24V LiFePO₄ comandado por um Raspberry Pi, com degradação progressiva da velocidade das bombas conforme o estado de carga.</td>
    <td>sozinho, ou a par do ha-reefbeat-component</td>
  </tr>
</table>

Estão todos documentados em conjunto na [página do projeto ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

## Dispositivos suportados

O seu dispositivo não é suportado? Entre em contato comigo.

> ✅ Suportado &nbsp;|&nbsp; 🧪 Não testado (pode funcionar) &nbsp;|&nbsp; ❌ Ainda não suportado

| Dispositivo | | Nome interno | Chave do produto | Estado |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (bomba de retorno) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic DC Runner (bomba de escumador) | <img alt="escumador" src="doc/img/skimmer.png" width="200" /> | `DC_Runner` | `00276aa006684c05805c297f60058c3d` | ✅ |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Todos estes dispositivos utilizam a plataforma IoT Gizwits (o mesmo backend que a aplicação oficial Aqua Medic). O suporte a dispositivos adicionais podrá ser adicionado em versões futuras.

---

## Instalação

### Via HACS

A integração está agora oficialmente no HACS. Basta procurar por **Aqua Medic** na aba Integrações e instale.

Ou use o botão de instalação direta:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-aquamedic-component&category=integration)

Em seguida, reinicie o Home Assistant.

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

<!-- maintenance-section:start -->

## Manutenção

A integração acompanha as tarefas de limpeza e desgaste de cada bomba. Cada tarefa tem três entidades: um **botão** para registar que está feita, um **cursor** para ajustar o intervalo e um **interruptor** para silenciar os seus alertas. Nada é enviado para a nuvem — o estado é guardado localmente, por entrada de configuração.

A bomba de retorno DC Runner e a bomba do escumador partilham o mesmo firmware e a mesma product key Gizwits, por isso a API não as distingue. Declare-o uma vez no seletor **Função da bomba**: a lista de tarefas acompanha (a integração recarrega para o aplicar). Enquanto a função for *Não definido*, uma DC Runner não tem qualquer tarefa. As EcoDrift / SmartDrift nunca perguntam.

| Bomba | Tarefa | Predefinição | Intervalo |
|---|---|---|---|
| EcoDrift / SmartDrift | Limpar o rotor e o cesto de filtragem | 2 | 1–3 |
| EcoDrift / SmartDrift | Descalcificar a bomba | 6 | 3–9 |
| EcoDrift / SmartDrift | Substituir o rotor e os rolamentos | 18 | 12–24 |
| DC Runner (retorno) | Limpar o cesto de aspiração | 6 w | 3–9 w |
| DC Runner (retorno) | Limpar o rotor e a câmara da bomba | 4 | 2–6 |
| DC Runner (retorno) | Substituir o rotor e os rolamentos | 18 | 12–24 |
| DC Runner (escumador) | Limpar o copo coletor | 2 w | 1–4 w |
| DC Runner (escumador) | Limpar o venturi e o tubo de ar | 4 w | 2–8 w |
| DC Runner (escumador) | Limpar o rotor de agulhas | 2 | 1–4 |
| DC Runner (escumador) | Descalcificar o corpo do escumador | 6 | 3–12 |
| DC Runner (escumador) | Substituir o rotor de agulhas e os rolamentos | 18 | 12–24 |

> Valores em meses, exceto se seguidos de `w` (semanas). A Aqua Medic não publica qualquer intervalo numérico: estes valores vêm da prática em aquário de recife e são ajustáveis bomba a bomba.

### Notificações

A integração nunca notifica sozinha, de propósito. Isso é feito pelo blueprint **Aqua Medic watch** incluído no repositório, que cobre também as falhas de hardware e as bombas offline. Clique no botão abaixo e confirme a importação no Home Assistant:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-aquamedic-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faquamedic_alerts.en.yaml)

Está disponível uma versão francesa: [`aquamedic_alerts.fr.yaml`](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/blueprints/automation/aquamedic_alerts.fr.yaml).

As tarefas aparecem também na vista de manutenção do [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), ao lado das do Red Sea: ambas as integrações publicam o mesmo contrato de entidades `reef_role`.

<!-- maintenance-section:end -->

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

