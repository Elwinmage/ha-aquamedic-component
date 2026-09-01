# Aquamedic 🌊
> Część **[Ekosystemu ReefTech Project](https://elwinmage.github.io/reeftank/pl.html)**
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

Steruj pompami Aqua Medic z Home Assistant przez API chmury Gizwits.

---

<!-- ecosystem:start -->

## Powiązane projekty

Projekty ReefTech uzupełniają się: integracje wprowadzają sprzęt do Home Assistant, karta go wyświetla i steruje nim, a zasilanie awaryjne utrzymuje go w ruchu podczas przerwy w zasilaniu. Każdy działa również samodzielnie.

<table>
  <tr>
    <th width="100px"></th>
    <th>Projekt</th>
    <th>Rola</th>
    <th>Współpracuje z</th>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/main/icon.png" width="64" alt="ha-reefbeat-component" /></td>
    <td>🐠<br /><a href="https://github.com/Elwinmage/ha-reefbeat-component"><b>ha-reefbeat-component</b></a></td>
    <td>Urządzenia Red Sea ReefBeat, sterowane lokalnie bez chmury: ReefATO+, ReefControl, ReefControl-Power, ReefDose, ReefLed, ReefMat, ReefRun i ReefWave.<br />blueprint alertów dla nietypowych trybów, kalibracji i niskiego poziomu baterii. <a href="https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Elwinmage/ha-reefbeat-component/refs/heads/main/blueprints/automation/redsea_alerts.en.yaml"><img src="https://my.home-assistant.io/badges/blueprint_import.svg" alt="Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled." /></a></td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-aquamedic-component/main/icon.png" width="64" alt="ha-aquamedic-component" /></td>
    <td>🌊<br /><b>ha-aquamedic-component</b><br /><i>(to repozytorium)</i></td>
    <td>Pompy Aqua Medic przez chmurowe API Gizwits: pompy cyrkulacyjne EcoDrift i SmartDrift, pompy DC Runner obiegowe i do odpieniacza.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-maintenance-component/main/icon.png" width="64" alt="ha-reef-maintenance-component" /></td>
    <td>🐙<br /><a href="https://github.com/Elwinmage/ha-reef-maintenance-component"><b>ha-reef-maintenance-component</b></a></td>
    <td>Śledzenie czyszczenia i zużycia sprzętu, do którego Home Assistant nie ma dostępu: pompy cyrkulacyjne, pompy obiegowe, odpieniacze, reaktory, wszystko co obsługujesz ręcznie.</td>
    <td>ha-reef-card</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-card/main/icon.png" width="64" alt="ha-reef-card" /></td>
    <td>🪸<br /><a href="https://github.com/Elwinmage/ha-reef-card"><b>ha-reef-card</b></a></td>
    <td>Interaktywny widok graficzny każdego urządzenia na pulpicie i jedyny sposób edycji zaawansowanych harmonogramów. Odczytuje trzy integracje przez wspólny kontrakt <code>reef_role</code>, bez konfiguracji po stronie karty.</td>
    <td>wszystkie trzy integracje</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/ha-reef-blueprints/main/icon.png" width="64" alt="ha-reef-blueprints" /></td>
    <td>🐬<br /><a href="https://github.com/Elwinmage/ha-reef-blueprints"><b>ha-reef-blueprints</b></a></td>
    <td>Blueprinty powiadomień wspólne dla całego ekosystemu: zaległe konserwacje znajdowane przez kontrakt <code>reef_role</code> oraz urządzenia, które przestały odpowiadać. Osiem języków.</td>
    <td>wszystkie trzy integracje</td>
  </tr>
  <tr>
    <td><img src="https://raw.githubusercontent.com/Elwinmage/reefbeatEnergyBackup/main/icon.png" width="64" alt="reefbeatEnergyBackup" /></td>
    <td>⚡<br /><a href="https://github.com/Elwinmage/reefbeatEnergyBackup"><b>reefbeatEnergyBackup</b></a></td>
    <td>Zasilanie awaryjne na wypadek przerw w zasilaniu. Pakiet 24V LiFePO₄ sterowany przez Raspberry Pi, ze stopniowym obniżaniem prędkości pomp zależnie od stanu naładowania.</td>
    <td>samodzielnie lub razem z ha-reefbeat-component</td>
  </tr>
</table>

Wszystkie są udokumentowane razem na [stronie projektu ReefTech](https://elwinmage.github.io/reeftank/).

<!-- ecosystem:end -->

## Obsługiwane urządzenia

Twoje urządzenie nie jest obsługiwane? Skontaktuj się ze mną.

> ✅ Obsługiwane &nbsp;|&nbsp; 🧪 Niesprawdzone (może działać) &nbsp;|&nbsp; ❌ Jeszcze nie obsługiwane

| Urządzenie | | Nazwa wewnętrzna | Klucz produktu | Status |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (pompa powrotna) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic DC Runner (pompa odpieniacza) | <img alt="odpieniacza" src="doc/img/skimmer.png" width="200" /> | `DC_Runner` | `00276aa006684c05805c297f60058c3d` | ✅ |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Wszystkie te urządzenia korzystają z platformy IoT Gizwits (ten sam backend co oficjalna aplikacja Aqua Medic). Obsługa dodatkowych urządzeń może zostać dodana w przyszłych wersjach.

---

## Instalacja

### Przez HACS

Integracja jest teraz oficjalnie w HACS. Po prostu wyszukaj **Aqua Medic** w karcie Integracje i zainstaluj.

Lub użyj przycisku instalacji bezpośredniej:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Elwinmage&repository=ha-aquamedic-component&category=integration)

Następnie zrestartuj Home Assistant.

---

## Encje

### EcoDrift / SmartDrift

#### Przełączniki

| Encja | Opis |
|---|---|
| **Zasilanie** | Główny włącznik/wyłącznik |
| **Typ fali** | Tryb impulsu (wył.) / Tryb pływów (wł.) |
| **Tryb karmienia** | Aktywuje przerwę karmienia |
| **Timer** | Włącza tryb programowy |
| **Tryb sterowania 0-10V** | Po włączeniu dezaktywuje suwak przepływu |

#### Listy wyboru

| Encja | Opcje |
|---|---|
| **Tryb fali** | Klasyczna fala · Fala sinusoidalna · Losowa fala · Stały przepływ |
| **Sprzężenie** | Niezależny · Master · Slave |

#### Liczby

| Encja | Zakres | Opis |
|---|---|---|
| **Przepływ** | 0–100 % | Przepływ silnika (wyłączony w trybie 0-10V) |
| **Częstotliwość** | 0–100 % | Częstotliwość fal |
| **Czas karmienia** | 1–60 min | Czas trwania przerwy karmienia |

#### Czujniki binarne (diagnostyka)

| Encja | Opis |
|---|---|
| **Błąd nadprądu** | Nadprąd / zwarcie silnika |
| **Błąd nadnapięcia** | Nadnapięcie silnika |
| **Błąd przegrzania** | Temperatura silnika zbyt wysoka |
| **Błąd podnapięcia** | Podnapięcie silnika |
| **Błąd zablokowanego wirnika** | Silnik zablokowany / zakleszczony |
| **Błąd biegu jałowego** | Pompa pracuje na sucho |
| **Błąd komunikacji UART** | Błąd komunikacji moduł ↔ płyta główna |

#### Przycisk (diagnostyka)

| Encja | Opis |
|---|---|
| **Odśwież** | Wymusza natychmiastowe odświeżenie |

### DC Runner (pompa powrotna)

> 🧪 Wsparcie jest zaimplementowane, ale **jeszcze nie przetestowane na prawdziwym sprzęcie**. Opinie mile widziane.

#### Przełączniki

| Encja | Opis |
|---|---|
| **Zasilanie** | Główny włącznik/wyłącznik |
| **Tryb karmienia** | Wstrzymuje przepływ na 10 minut |
| **Tryb sterowania 0-10V** | Po włączeniu dezaktywuje suwak prędkości (pompa sterowana zewnętrznym sygnałem 0-10V) |

#### Liczby

| Encja | Zakres | Opis |
|---|---|---|
| **Przepływ** | 30–100 % | Prędkość pompy (minimum 30 % — poniżej silnik może się zatrzymać) |

### DC Skimmer (pompa odpieniacza DC Runner)

> ✅ Na podstawie rzeczywistego zrzutu datapointów urządzenia.

#### Przełączniki

| Encja | Opis |
|---|---|
| **Zasilanie** | Główny włącznik/wyłącznik |
| **Tryb karmienia** | Aktywuje przerwę karmienia |
| **Timer** | Włącza program harmonogramu |
| **Tryb sterowania 0-10V** | Po włączeniu dezaktywuje suwak prędkości (pompa sterowana zewnętrznym sygnałem 0-10V) |

#### Listy wyboru

| Encja | Opcje |
|---|---|
| **Tryb harmonogramu** | Stop · Automatyczny · Karmienie |

#### Liczby

| Encja | Zakres | Opis |
|---|---|---|
| **Prędkość silnika** | 30–100 % | Prędkość pompy (minimum 30 % — poniżej silnik może się zatrzymać; wyłączone w trybie 0-10V) |
| **Czas karmienia** | 1–60 min | Czas trwania przerwy karmienia |
| **Prędkość harmonogramu** | 0–100 % | Prędkość używana przez program harmonogramu |
| **Czas karmienia harmonogramu** | 1–60 min | Czas karmienia używany przez program harmonogramu |

#### Czujniki binarne (diagnostyka)

| Encja | Opis |
|---|---|
| **Błąd nadprądu** | Nadprąd / zwarcie silnika |
| **Błąd nadnapięcia** | Nadnapięcie silnika |
| **Błąd przegrzania** | Temperatura silnika zbyt wysoka |
| **Błąd podnapięcia** | Podnapięcie silnika |
| **Błąd zablokowanego wirnika** | Silnik zablokowany / zakleszczony |
| **Błąd biegu jałowego** | Pompa pracuje na sucho |
| **Błąd komunikacji UART** | Błąd komunikacji moduł ↔ płyta główna |

#### Przycisk (diagnostyka)

| Encja | Opis |
|---|---|
| **Odśwież** | Wymusza natychmiastowe odświeżenie |

> **O sterowaniu 0-10V:** każdy kontroler DC Runner ma fizyczne wejście 0-10V do zewnętrznego sterownika akwariowego (Apex, GHL, …). To port sprzętowy, a nie wartość w chmurze, więc nie pojawia się jako atrybut urządzenia — przełącznik *Tryb sterowania 0-10V* to lokalna flaga Home Assistant, która dezaktywuje suwak prędkości, gdy pompa jest sterowana zewnętrznie. Zgodnie z instrukcją Aqua Medic, w trybie 0-10V pompa musi pracować z mocą **≥ 60 %**.

---

<!-- maintenance-section:start -->

## Konserwacja

Integracja śledzi zadania czyszczenia i zużycia każdej pompy. Każde zadanie ma trzy encje: **przycisk** do odnotowania wykonania, **suwak** do zmiany interwału oraz **przełącznik** do wyciszenia jego powiadomień. Nic nie trafia do chmury — stan jest zapisywany lokalnie, dla każdego wpisu konfiguracji.

Pompa obiegowa DC Runner i pompa odpieniacza mają to samo oprogramowanie i ten sam product key Gizwits, więc API ich nie rozróżnia. Zadeklaruj to raz w selektorze **Rola pompy** — lista zadań się dostosuje (integracja przeładuje się, aby to zastosować). Dopóki rola to *Nieokreślona*, DC Runner nie ma żadnego zadania. EcoDrift / SmartDrift nigdy o to nie pytają.

| Pompa | Zadanie | Domyślnie | Zakres |
|---|---|---|---|
| EcoDrift / SmartDrift | Wyczyść wirnik i kosz filtra | 2 | 1–3 |
| EcoDrift / SmartDrift | Odkamień pompę | 6 | 3–9 |
| EcoDrift / SmartDrift | Wymień wirnik i łożyska | 18 | 12–24 |
| DC Runner (obieg) | Wyczyść kosz ssawny | 6 w | 3–9 w |
| DC Runner (obieg) | Wyczyść wirnik i komorę pompy | 4 | 2–6 |
| DC Runner (obieg) | Wymień wirnik i łożyska | 18 | 12–24 |
| DC Runner (odpieniacz) | Wyczyść kubek odpieniacza | 2 w | 1–4 w |
| DC Runner (odpieniacz) | Wyczyść venturi i wężyk powietrza | 4 w | 2–8 w |
| DC Runner (odpieniacz) | Wyczyść wirnik igiełkowy | 2 | 1–4 |
| DC Runner (odpieniacz) | Odkamień korpus odpieniacza | 6 | 3–12 |
| DC Runner (odpieniacz) | Wymień wirnik igiełkowy i łożyska | 18 | 12–24 |

> Wartości w miesiącach, chyba że z `w` (tygodnie). Aqua Medic nie podaje żadnych liczb: te wartości pochodzą z praktyki akwarystyki rafowej i można je zmienić dla każdej pompy.

### Powiadomienia

Integracja celowo nigdy nie powiadamia sama. Robi to blueprint **Aqua Medic watch** dołączony do repozytorium, który obejmuje także awarie sprzętowe i pompy offline. Kliknij przycisk poniżej i potwierdź import w Home Assistant:

[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-aquamedic-component%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Faquamedic_alerts.en.yaml)

Dostępna jest wersja francuska: [`aquamedic_alerts.fr.yaml`](https://github.com/Elwinmage/ha-aquamedic-component/blob/main/blueprints/automation/aquamedic_alerts.fr.yaml).

Zadania pojawiają się również w widoku konserwacji [ha-reef-card](https://github.com/Elwinmage/ha-reef-card), obok zadań Red Sea: obie integracje publikują ten sam kontrakt encji `reef_role`.

<!-- maintenance-section:end -->

## Konfiguracja

Przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację → Aqua Medic**.

| Pole | Opis |
|---|---|
| **E-mail** | Adres e-mail konta Aqua Medic |
| **Hasło** | Hasło konta Aqua Medic |
| **Serwer Gizwits** | Serwer regionalny — **Europa** dla użytkowników UE |
| **Interwał odświeżania** | Częstotliwość odpytywania (5–300 s, domyślnie 30 s) |

Właściwy serwer jest automatycznie wybierany na podstawie języka Home Assistant.

Po konfiguracji interwał można zmienić w **Ustawienia → Urządzenia i usługi → Aqua Medic → Konfiguruj**.

---

## Rozwój

### Lokalny symulator

Symulator chmury Gizwits (`scripts/gizwits_simulator.py`) pozwala testować integrację bez prawdziwego sprzętu i dostępu do chmury. Konfiguruje się go w `scripts/gizwits_sim_config.json`:

| Klucz | Opis |
|---|---|
| `username` / `password` | Dane logowania, których ma użyć integracja |
| `virtual_ip` | IP, na którym nasłuchuje symulator (`127.0.0.1` pomija wirtualne IP) |
| `interface` | Interfejs sieciowy dla wirtualnego IP (opcjonalny; jeśli pominięty, interfejs trasy domyślnej jest wykrywany automatycznie, z `eth0` jako rezerwą; można nadpisać przez `-i/--interface`) |
| `port` | Port (domyślnie `8080`) |
| `devices` | Lista `{ "type": ..., "count": N }`; typy: `smartdrift`, `dc_runner` (pompa powrotna), `dc_skimmer` |

Uruchomienie: `sudo python3 scripts/gizwits_simulator.py` (root wymagany do dodania wirtualnego IP).

Aby region **Symulator** pojawił się w kreatorze konfiguracji, utwórz lokalny plik-flagę (ignorowany przez git, nigdy go nie commituj):

```bash
cp custom_components/aquamedic/simulator_enabled.example custom_components/aquamedic/.simulator_enabled
```

Uruchom ponownie Home Assistant, dodaj integrację i wybierz *Symulator*; zostaniesz poproszony o adres URL symulatora (domyślnie `http://localhost:8080`) i dane logowania.

---

## Licencja

MIT – zobacz [LICENSE](../../LICENSE).

