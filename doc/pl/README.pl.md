# Aquamedic
> Część **[Ekosystemu ReefTech Project](https://elwinmage.github.io/reeftank/pl.html)**
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

Steruj pompami Aqua Medic z Home Assistant przez API chmury Gizwits.

---

## Obsługiwane urządzenia

Twoje urządzenie nie jest obsługiwane? Skontaktuj się ze mną.

> ✅ Obsługiwane &nbsp;|&nbsp; 🧪 Niesprawdzone (może działać) &nbsp;|&nbsp; ❌ Jeszcze nie obsługiwane

| Urządzenie | | Nazwa wewnętrzna | Klucz produktu | Status |
|---|---|---|---|---|
| Aqua Medic EcoDrift / SmartDrift x.1 / x.3 | <img width="368" height="1024" alt="image" src="https://github.com/user-attachments/assets/3cc74acc-aab7-4bbf-a386-51155cf11943" /> | `Current_Pump` | `63632f4902094055ab3fd994c0d612fa` | ✅ |
| Aqua Medic DC Runner x.1 / x.2 / x.3 (pompa powrotna) | <img width="368" height="441" alt="image" src="https://github.com/user-attachments/assets/99d5e986-a100-41b9-94dd-30b38d9b3661" /> | `DC_Runner` | `8879684725d14066922374e50889f893` | 🧪 |
| Aqua Medic Reefdoser EVO | <img width="458" height="458" alt="image" src="https://github.com/user-attachments/assets/b5e98032-9cea-4647-9443-18d4d68a275d" />| `Dosing_Pump` | `a1f9488390b4458f9676677f51664324` | ❌ |
| Aqua Medic T-Controller Twin | | `Temp_Ctrl` | `f6a8e5d2c1b04a9e8d7c6b5a4f3e2d1c` | ❌ |
| Aqua Medic Aquarius / Spectrus | | `Light_Ctrl` | `7d2e9b8a1c3f4e5d6a7b8c9d0e1f2a3b` | ❌ |

Wszystkie te urządzenia korzystają z platformy IoT Gizwits (ten sam backend co oficjalna aplikacja Aqua Medic). Obsługa dodatkowych urządzeń może zostać dodana w przyszłych wersjach.

---

## Instalacja

### Przez HACS (zalecane)

1. W HACS przejdź do **Integracje → ⋮ → Niestandardowe repozytoria**
2. Dodaj `https://github.com/Elwinmage/ha-aquamedic-component` jako **Integrację**
3. Wyszukaj **Aqua Medic** i zainstaluj
4. Uruchom ponownie Home Assistant

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

### DC Runner

> 🧪 Wsparcie jest zaimplementowane, ale **jeszcze nie przetestowane na prawdziwym sprzęcie**. Opinie mile widziane.

#### Przełączniki

| Encja | Opis |
|---|---|
| **Zasilanie** | Główny włącznik/wyłącznik |
| **Tryb karmienia** | Wstrzymuje przepływ na 10 minut |
| **Tryb sterowania 0-10V** | Po włączeniu przepływ sterowany zewnętrznym sygnałem 0-10V |

#### Liczby

| Encja | Zakres | Opis |
|---|---|---|
| **Przepływ** | 30–100 % | Prędkość pompy (minimum 30 % — poniżej silnik może się zatrzymać) |

#### Czujniki binarne (diagnostyka)

| Encja | Opis |
|---|---|
| **Błąd biegu jałowego** | Automatyczne wyłączenie jeśli brak wody przez 2 min |
| **Błąd zablokowanego wirnika** | Wykryto mechaniczną przeszkodę |
| **Błąd napięcia** | Napięcie zasilania poza zakresem |

---

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

## Licencja

MIT – zobacz [LICENSE](../../LICENSE).

