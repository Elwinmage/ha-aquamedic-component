#!/usr/bin/env python3
"""One-shot generator for the maintenance translation keys.

Kept in the repo so the wording of the 11 maintenance tasks can be reviewed
and regenerated in one place instead of hand-editing nine JSON files. Running
it again is idempotent: existing keys are overwritten, unrelated keys are left
untouched.

    python3 scripts/gen_maintenance_translations.py
"""

from __future__ import annotations

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BASE = os.path.join(REPO_ROOT, "custom_components", "aquamedic")
TRANSLATIONS = os.path.join(BASE, "translations")

# task key -> display unit of the companion interval number entity.
# Must stay in sync with maintenance.py.
TASK_UNITS: dict[str, str] = {
    "drift_rotor_clean": "months",
    "drift_descale": "months",
    "drift_impeller_replace": "months",
    "runner_strainer_clean": "weeks",
    "runner_impeller_clean": "months",
    "runner_impeller_replace": "months",
    "skimmer_cup_clean": "weeks",
    "skimmer_venturi_clean": "weeks",
    "skimmer_needle_wheel_clean": "months",
    "skimmer_body_descale": "months",
    "skimmer_needle_wheel_replace": "months",
}

TASK_ORDER = list(TASK_UNITS)

# Base task names per language, in TASK_ORDER order.
NAMES: dict[str, list[str]] = {
    "en": [
        "Clean impeller and filter basket",
        "Descale pump",
        "Replace impeller and bearings",
        "Clean suction strainer",
        "Clean impeller and pump chamber",
        "Replace impeller and bearings",
        "Clean collection cup",
        "Clean venturi and air line",
        "Clean needle wheel",
        "Descale skimmer body",
        "Replace needle wheel and bearings",
    ],
    "fr": [
        "Nettoyer le rotor et le panier de filtration",
        "Détartrer la pompe",
        "Remplacer le rotor et les roulements",
        "Nettoyer la crépine d'aspiration",
        "Nettoyer le rotor et la chambre de pompe",
        "Remplacer le rotor et les roulements",
        "Nettoyer le gobelet",
        "Nettoyer le venturi et le tuyau d'air",
        "Nettoyer le rotor à aiguilles",
        "Détartrer le corps de l'écumeur",
        "Remplacer le rotor à aiguilles et les roulements",
    ],
    "de": [
        "Rotor und Filterkorb reinigen",
        "Pumpe entkalken",
        "Rotor und Lager ersetzen",
        "Ansaugkorb reinigen",
        "Rotor und Pumpenkammer reinigen",
        "Rotor und Lager ersetzen",
        "Schaumtopf reinigen",
        "Venturi und Luftschlauch reinigen",
        "Nadelrad reinigen",
        "Abschäumerkörper entkalken",
        "Nadelrad und Lager ersetzen",
    ],
    "es": [
        "Limpiar el rotor y la cesta de filtración",
        "Descalcificar la bomba",
        "Sustituir el rotor y los rodamientos",
        "Limpiar la cesta de aspiración",
        "Limpiar el rotor y la cámara de la bomba",
        "Sustituir el rotor y los rodamientos",
        "Limpiar el vaso colector",
        "Limpiar el venturi y el tubo de aire",
        "Limpiar el rotor de agujas",
        "Descalcificar el cuerpo del skimmer",
        "Sustituir el rotor de agujas y los rodamientos",
    ],
    "it": [
        "Pulire il rotore e il cestello filtrante",
        "Decalcificare la pompa",
        "Sostituire il rotore e i cuscinetti",
        "Pulire il cestello di aspirazione",
        "Pulire il rotore e la camera della pompa",
        "Sostituire il rotore e i cuscinetti",
        "Pulire il bicchiere di raccolta",
        "Pulire il venturi e il tubo dell'aria",
        "Pulire la girante ad aghi",
        "Decalcificare il corpo dello schiumatoio",
        "Sostituire la girante ad aghi e i cuscinetti",
    ],
    "nl": [
        "Rotor en filterkorf reinigen",
        "Pomp ontkalken",
        "Rotor en lagers vervangen",
        "Aanzuigkorf reinigen",
        "Rotor en pompkamer reinigen",
        "Rotor en lagers vervangen",
        "Opvangbeker reinigen",
        "Venturi en luchtslang reinigen",
        "Naaldrotor reinigen",
        "Skimmerbehuizing ontkalken",
        "Naaldrotor en lagers vervangen",
    ],
    "pl": [
        "Wyczyść wirnik i kosz filtra",
        "Odkamień pompę",
        "Wymień wirnik i łożyska",
        "Wyczyść kosz ssawny",
        "Wyczyść wirnik i komorę pompy",
        "Wymień wirnik i łożyska",
        "Wyczyść kubek odpieniacza",
        "Wyczyść venturi i wężyk powietrza",
        "Wyczyść wirnik igiełkowy",
        "Odkamień korpus odpieniacza",
        "Wymień wirnik igiełkowy i łożyska",
    ],
    "pt": [
        "Limpar o rotor e o cesto de filtragem",
        "Descalcificar a bomba",
        "Substituir o rotor e os rolamentos",
        "Limpar o cesto de aspiração",
        "Limpar o rotor e a câmara da bomba",
        "Substituir o rotor e os rolamentos",
        "Limpar o copo coletor",
        "Limpar o venturi e o tubo de ar",
        "Limpar o rotor de agulhas",
        "Descalcificar o corpo do escumador",
        "Substituir o rotor de agulhas e os rolamentos",
    ],
}

# Suffix appended to the interval number entity name, per language and unit.
UNITS: dict[str, dict[str, str]] = {
    "en": {"weeks": "weeks", "months": "months"},
    "fr": {"weeks": "semaines", "months": "mois"},
    "de": {"weeks": "Wochen", "months": "Monate"},
    "es": {"weeks": "semanas", "months": "meses"},
    "it": {"weeks": "settimane", "months": "mesi"},
    "nl": {"weeks": "weken", "months": "maanden"},
    "pl": {"weeks": "tygodnie", "months": "miesiące"},
    "pt": {"weeks": "semanas", "months": "meses"},
}

# Suffix appended to the notification switch name, per language.
NOTIFY: dict[str, str] = {
    "en": "notifications",
    "fr": "notifications",
    "de": "Benachrichtigungen",
    "es": "notificaciones",
    "it": "notifiche",
    "nl": "meldingen",
    "pl": "powiadomienia",
    "pt": "notificações",
}

# Pump role select: entity name then the three option labels.
PUMP_ROLE: dict[str, dict[str, str]] = {
    "en": {
        "name": "Pump role",
        "unknown": "Not set",
        "return": "Return pump",
        "skimmer": "Skimmer pump",
    },
    "fr": {
        "name": "Rôle de la pompe",
        "unknown": "Non défini",
        "return": "Pompe de remontée",
        "skimmer": "Pompe d'écumeur",
    },
    "de": {
        "name": "Pumpenrolle",
        "unknown": "Nicht festgelegt",
        "return": "Rückförderpumpe",
        "skimmer": "Abschäumerpumpe",
    },
    "es": {
        "name": "Función de la bomba",
        "unknown": "Sin definir",
        "return": "Bomba de retorno",
        "skimmer": "Bomba de skimmer",
    },
    "it": {
        "name": "Ruolo della pompa",
        "unknown": "Non definito",
        "return": "Pompa di risalita",
        "skimmer": "Pompa dello schiumatoio",
    },
    "nl": {
        "name": "Pomprol",
        "unknown": "Niet ingesteld",
        "return": "Opvoerpomp",
        "skimmer": "Skimmerpomp",
    },
    "pl": {
        "name": "Rola pompy",
        "unknown": "Nieokreślona",
        "return": "Pompa obiegowa",
        "skimmer": "Pompa odpieniacza",
    },
    "pt": {
        "name": "Função da bomba",
        "unknown": "Não definido",
        "return": "Bomba de retorno",
        "skimmer": "Bomba do escumador",
    },
}


def build(lang: str) -> dict[str, dict]:
    """Return the entity sub-tree to merge for one language."""
    buttons: dict[str, dict] = {}
    numbers: dict[str, dict] = {}
    switches: dict[str, dict] = {}

    for key, name in zip(TASK_ORDER, NAMES[lang]):
        unit = TASK_UNITS[key]
        buttons[f"maint_{key}"] = {"name": name}
        numbers[f"maint_{key}_interval_{unit}"] = {
            "name": f"{name} ({UNITS[lang][unit]})"
        }
        switches[f"maint_{key}_notify"] = {"name": f"{name} ({NOTIFY[lang]})"}

    role = PUMP_ROLE[lang]
    selects = {
        "pump_role": {
            "name": role["name"],
            "state": {
                "unknown": role["unknown"],
                "return": role["return"],
                "skimmer": role["skimmer"],
            },
        }
    }
    return {
        "button": buttons,
        "number": numbers,
        "switch": switches,
        "select": selects,
    }


def patch(path: str, lang: str) -> None:
    """Merge the generated keys into one translation file, in place."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    entity = data.setdefault("entity", {})
    for platform, keys in build(lang).items():
        target = entity.setdefault(platform, {})
        for key, payload in keys.items():
            target[key] = payload

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"  patched {os.path.relpath(path, REPO_ROOT)}")


def main() -> None:
    for lang in NAMES:
        patch(os.path.join(TRANSLATIONS, f"{lang}.json"), lang)
    # strings.json is the English source of truth shipped to HA.
    patch(os.path.join(BASE, "strings.json"), "en")


if __name__ == "__main__":
    main()
