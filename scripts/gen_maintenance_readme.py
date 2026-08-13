#!/usr/bin/env python3
"""One-shot injector for the "Maintenance" README section (7 languages).

Kept next to gen_maintenance_translations.py so the wording of the feature is
reviewed in one place. The section is inserted right before the
"Configuration" heading of each README; running the script again replaces the
previously inserted block instead of duplicating it.

    python3 scripts/gen_maintenance_readme.py
"""

from __future__ import annotations

import os
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

REPO_URL = "https://github.com/Elwinmage/ha-aquamedic-component"
BLUEPRINT_DIR = f"{REPO_URL}/blob/main/blueprints/automation"
IMPORT_BADGE = (
    "[![Open your Home Assistant instance and show the blueprint import dialog "
    "with a specific blueprint pre-filled.]"
    "(https://my.home-assistant.io/badges/blueprint_import.svg)]"
    "(https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url="
    "https%3A%2F%2Fgithub.com%2FElwinmage%2Fha-aquamedic-component%2Fblob%2Fmain"
    "%2Fblueprints%2Fautomation%2Faquamedic_alerts.en.yaml)"
)

MARKER_START = "<!-- maintenance-section:start -->"
MARKER_END = "<!-- maintenance-section:end -->"

# README path -> (language, heading it must be inserted before)
FILES: dict[str, tuple[str, str]] = {
    "README.md": ("en", "## Configuration"),
    "doc/fr/README.fr.md": ("fr", "## Configuration"),
    "doc/de/README.de.md": ("de", "## Konfiguration"),
    "doc/es/README.es.md": ("es", "## Configuración"),
    "doc/it/README.it.md": ("it", "## Configurazione"),
    "doc/pl/README.pl.md": ("pl", "## Konfiguracja"),
    "doc/pt/README.pt.md": ("pt", "## Configuração"),
}

# Section title, intro, pump role paragraph, task table header, blueprint text.
# Every value is a string except "pumps", which holds the per-group pump labels.
TEXT: dict[str, dict[str, Any]] = {
    "en": {
        "title": "Maintenance",
        "intro": (
            "The integration tracks the cleaning and wear tasks of each pump. "
            "Every task comes with three entities: a **button** to record that "
            "the job is done, a **slider** to adjust the interval, and a "
            "**switch** to mute its alerts. Nothing is sent to the cloud — the "
            "state is stored locally, per config entry."
        ),
        "role": (
            "The DC Runner return pump and the DC Skimmer share the same "
            "firmware and the same Gizwits product key, so the API cannot tell "
            "them apart. Declare it once with the **Pump role** select: the "
            "task list follows (the integration reloads itself to apply it). "
            "As long as the role is *Not set*, a DC Runner carries no "
            "maintenance task. EcoDrift / SmartDrift pumps never ask."
        ),
        "table_head": "| Pump | Task | Default | Range |",
        "blueprint_title": "Notifications",
        "blueprint": (
            "The integration never notifies by itself, on purpose. The "
            "**Aqua Medic watch** blueprint shipped with the repository does "
            "it, and also covers hardware faults and offline pumps. Click the "
            "button below and confirm the import in Home Assistant:"
        ),
        "blueprint_fr": (
            "A French version is available as [`aquamedic_alerts.fr.yaml`]"
            f"({BLUEPRINT_DIR}/aquamedic_alerts.fr.yaml)."
        ),
        "card": (
            "Tasks are also picked up by the maintenance view of "
            "[ha-reef-card](https://github.com/Elwinmage/ha-reef-card), next to "
            "the Red Sea ones: both integrations publish the same `reef_role` "
            "entity contract."
        ),
        "pumps": {
            "drift": "EcoDrift / SmartDrift",
            "return": "DC Runner (return)",
            "skimmer": "DC Runner (skimmer)",
        },
    },
    "fr": {
        "title": "Maintenance",
        "intro": (
            "L'intégration suit les tâches de nettoyage et d'usure de chaque "
            "pompe. Chaque tâche expose trois entités : un **bouton** pour "
            "enregistrer que c'est fait, un **curseur** pour ajuster "
            "l'intervalle, et un **interrupteur** pour couper ses alertes. "
            "Rien n'est envoyé au cloud — l'état est stocké localement, par "
            "entrée de configuration."
        ),
        "role": (
            "La pompe de remontée DC Runner et l'écumeur DC Skimmer partagent "
            "le même firmware et la même product key Gizwits : l'API ne peut "
            "pas les distinguer. Déclarez-le une fois via le select **Rôle de "
            "la pompe**, la liste des tâches suit (l'intégration se recharge "
            "pour l'appliquer). Tant que le rôle est *Non défini*, une DC "
            "Runner n'a aucune tâche. Les EcoDrift / SmartDrift ne posent "
            "jamais la question."
        ),
        "table_head": "| Pompe | Tâche | Défaut | Plage |",
        "blueprint_title": "Notifications",
        "blueprint": (
            "L'intégration ne notifie jamais d'elle-même, volontairement. "
            "C'est le rôle du blueprint **Aqua Medic watch** livré avec le "
            "dépôt, qui couvre aussi les défauts matériels et les pompes hors "
            "ligne. Cliquez sur le bouton ci-dessous et confirmez l'import "
            "dans Home Assistant :"
        ),
        "blueprint_fr": (
            "Une version française est disponible : [`aquamedic_alerts.fr.yaml`]"
            f"({BLUEPRINT_DIR}/aquamedic_alerts.fr.yaml)."
        ),
        "card": (
            "Les tâches remontent aussi dans la vue maintenance de "
            "[ha-reef-card](https://github.com/Elwinmage/ha-reef-card), à côté "
            "de celles de Red Sea : les deux intégrations publient le même "
            "contrat d'entités `reef_role`."
        ),
        "pumps": {
            "drift": "EcoDrift / SmartDrift",
            "return": "DC Runner (remontée)",
            "skimmer": "DC Runner (écumeur)",
        },
    },
    "de": {
        "title": "Wartung",
        "intro": (
            "Die Integration verfolgt die Reinigungs- und Verschleißaufgaben "
            "jeder Pumpe. Jede Aufgabe hat drei Entitäten: einen **Button**, um "
            "die Erledigung zu erfassen, einen **Schieberegler** für das "
            "Intervall und einen **Schalter**, um ihre Meldungen "
            "stummzuschalten. Nichts wird in die Cloud gesendet — der Zustand "
            "wird lokal je Konfigurationseintrag gespeichert."
        ),
        "role": (
            "Die DC-Runner-Rückförderpumpe und die DC-Skimmer-Pumpe teilen sich "
            "Firmware und Gizwits-Product-Key, die API kann sie also nicht "
            "unterscheiden. Legen Sie es einmal über die Auswahl "
            "**Pumpenrolle** fest, die Aufgabenliste folgt (die Integration "
            "lädt sich dafür neu). Solange die Rolle *Nicht festgelegt* ist, "
            "hat eine DC Runner keine Aufgabe. EcoDrift / SmartDrift fragen "
            "nie."
        ),
        "table_head": "| Pumpe | Aufgabe | Standard | Bereich |",
        "blueprint_title": "Benachrichtigungen",
        "blueprint": (
            "Die Integration benachrichtigt absichtlich nie selbst. Das "
            "übernimmt der mitgelieferte Blueprint **Aqua Medic watch**, der "
            "auch Hardwarefehler und Offline-Pumpen abdeckt. Klicken Sie auf "
            "die Schaltfläche unten und bestätigen Sie den Import in Home "
            "Assistant:"
        ),
        "blueprint_fr": (
            "Eine französische Fassung liegt als [`aquamedic_alerts.fr.yaml`]"
            f"({BLUEPRINT_DIR}/aquamedic_alerts.fr.yaml) bei."
        ),
        "card": (
            "Die Aufgaben erscheinen auch in der Wartungsansicht von "
            "[ha-reef-card](https://github.com/Elwinmage/ha-reef-card), neben "
            "denen von Red Sea: beide Integrationen veröffentlichen denselben "
            "`reef_role`-Entitätsvertrag."
        ),
        "pumps": {
            "drift": "EcoDrift / SmartDrift",
            "return": "DC Runner (Rückförderung)",
            "skimmer": "DC Runner (Abschäumer)",
        },
    },
    "es": {
        "title": "Mantenimiento",
        "intro": (
            "La integración realiza el seguimiento de las tareas de limpieza y "
            "desgaste de cada bomba. Cada tarea ofrece tres entidades: un "
            "**botón** para registrar que está hecha, un **deslizador** para "
            "ajustar el intervalo y un **interruptor** para silenciar sus "
            "avisos. No se envía nada a la nube: el estado se guarda "
            "localmente, por entrada de configuración."
        ),
        "role": (
            "La bomba de retorno DC Runner y la bomba de skimmer comparten "
            "firmware y product key de Gizwits, por lo que la API no puede "
            "distinguirlas. Decláralo una vez con el selector **Función de la "
            "bomba** y la lista de tareas se adapta (la integración se recarga "
            "para aplicarlo). Mientras la función sea *Sin definir*, una DC "
            "Runner no tiene ninguna tarea. Las EcoDrift / SmartDrift nunca lo "
            "preguntan."
        ),
        "table_head": "| Bomba | Tarea | Por defecto | Rango |",
        "blueprint_title": "Notificaciones",
        "blueprint": (
            "La integración nunca notifica por sí misma, a propósito. De eso se "
            "encarga el blueprint **Aqua Medic watch** incluido en el "
            "repositorio, que también cubre los fallos de hardware y las bombas "
            "sin conexión. Pulsa el botón siguiente y confirma la importación "
            "en Home Assistant:"
        ),
        "blueprint_fr": (
            "Hay una versión en francés: [`aquamedic_alerts.fr.yaml`]"
            f"({BLUEPRINT_DIR}/aquamedic_alerts.fr.yaml)."
        ),
        "card": (
            "Las tareas también aparecen en la vista de mantenimiento de "
            "[ha-reef-card](https://github.com/Elwinmage/ha-reef-card), junto a "
            "las de Red Sea: ambas integraciones publican el mismo contrato de "
            "entidades `reef_role`."
        ),
        "pumps": {
            "drift": "EcoDrift / SmartDrift",
            "return": "DC Runner (retorno)",
            "skimmer": "DC Runner (skimmer)",
        },
    },
    "it": {
        "title": "Manutenzione",
        "intro": (
            "L'integrazione tiene traccia delle attività di pulizia e usura di "
            "ogni pompa. Ogni attività espone tre entità: un **pulsante** per "
            "registrare che è fatta, un **cursore** per regolare l'intervallo e "
            "un **interruttore** per silenziarne gli avvisi. Nulla viene "
            "inviato al cloud: lo stato è salvato in locale, per voce di "
            "configurazione."
        ),
        "role": (
            "La pompa di risalita DC Runner e la pompa dello schiumatoio "
            "condividono firmware e product key Gizwits, quindi l'API non può "
            "distinguerle. Dichiaralo una volta con il selettore **Ruolo della "
            "pompa**: l'elenco delle attività si adegua (l'integrazione si "
            "ricarica per applicarlo). Finché il ruolo è *Non definito*, una DC "
            "Runner non ha alcuna attività. Le EcoDrift / SmartDrift non lo "
            "chiedono mai."
        ),
        "table_head": "| Pompa | Attività | Predefinito | Intervallo |",
        "blueprint_title": "Notifiche",
        "blueprint": (
            "L'integrazione non notifica mai da sola, di proposito. Se ne "
            "occupa il blueprint **Aqua Medic watch** incluso nel repository, "
            "che copre anche i guasti hardware e le pompe offline. Clicca il "
            "pulsante qui sotto e conferma l'importazione in Home Assistant:"
        ),
        "blueprint_fr": (
            "È disponibile una versione francese: [`aquamedic_alerts.fr.yaml`]"
            f"({BLUEPRINT_DIR}/aquamedic_alerts.fr.yaml)."
        ),
        "card": (
            "Le attività compaiono anche nella vista manutenzione di "
            "[ha-reef-card](https://github.com/Elwinmage/ha-reef-card), accanto "
            "a quelle Red Sea: entrambe le integrazioni pubblicano lo stesso "
            "contratto di entità `reef_role`."
        ),
        "pumps": {
            "drift": "EcoDrift / SmartDrift",
            "return": "DC Runner (risalita)",
            "skimmer": "DC Runner (schiumatoio)",
        },
    },
    "pl": {
        "title": "Konserwacja",
        "intro": (
            "Integracja śledzi zadania czyszczenia i zużycia każdej pompy. "
            "Każde zadanie ma trzy encje: **przycisk** do odnotowania "
            "wykonania, **suwak** do zmiany interwału oraz **przełącznik** do "
            "wyciszenia jego powiadomień. Nic nie trafia do chmury — stan jest "
            "zapisywany lokalnie, dla każdego wpisu konfiguracji."
        ),
        "role": (
            "Pompa obiegowa DC Runner i pompa odpieniacza mają to samo "
            "oprogramowanie i ten sam product key Gizwits, więc API ich nie "
            "rozróżnia. Zadeklaruj to raz w selektorze **Rola pompy** — lista "
            "zadań się dostosuje (integracja przeładuje się, aby to "
            "zastosować). Dopóki rola to *Nieokreślona*, DC Runner nie ma "
            "żadnego zadania. EcoDrift / SmartDrift nigdy o to nie pytają."
        ),
        "table_head": "| Pompa | Zadanie | Domyślnie | Zakres |",
        "blueprint_title": "Powiadomienia",
        "blueprint": (
            "Integracja celowo nigdy nie powiadamia sama. Robi to blueprint "
            "**Aqua Medic watch** dołączony do repozytorium, który obejmuje "
            "także awarie sprzętowe i pompy offline. Kliknij przycisk poniżej i "
            "potwierdź import w Home Assistant:"
        ),
        "blueprint_fr": (
            "Dostępna jest wersja francuska: [`aquamedic_alerts.fr.yaml`]"
            f"({BLUEPRINT_DIR}/aquamedic_alerts.fr.yaml)."
        ),
        "card": (
            "Zadania pojawiają się również w widoku konserwacji "
            "[ha-reef-card](https://github.com/Elwinmage/ha-reef-card), obok "
            "zadań Red Sea: obie integracje publikują ten sam kontrakt encji "
            "`reef_role`."
        ),
        "pumps": {
            "drift": "EcoDrift / SmartDrift",
            "return": "DC Runner (obieg)",
            "skimmer": "DC Runner (odpieniacz)",
        },
    },
    "pt": {
        "title": "Manutenção",
        "intro": (
            "A integração acompanha as tarefas de limpeza e desgaste de cada "
            "bomba. Cada tarefa tem três entidades: um **botão** para registar "
            "que está feita, um **cursor** para ajustar o intervalo e um "
            "**interruptor** para silenciar os seus alertas. Nada é enviado "
            "para a nuvem — o estado é guardado localmente, por entrada de "
            "configuração."
        ),
        "role": (
            "A bomba de retorno DC Runner e a bomba do escumador partilham o "
            "mesmo firmware e a mesma product key Gizwits, por isso a API não "
            "as distingue. Declare-o uma vez no seletor **Função da bomba**: a "
            "lista de tarefas acompanha (a integração recarrega para o "
            "aplicar). Enquanto a função for *Não definido*, uma DC Runner não "
            "tem qualquer tarefa. As EcoDrift / SmartDrift nunca perguntam."
        ),
        "table_head": "| Bomba | Tarefa | Predefinição | Intervalo |",
        "blueprint_title": "Notificações",
        "blueprint": (
            "A integração nunca notifica sozinha, de propósito. Isso é feito "
            "pelo blueprint **Aqua Medic watch** incluído no repositório, que "
            "cobre também as falhas de hardware e as bombas offline. Clique no "
            "botão abaixo e confirme a importação no Home Assistant:"
        ),
        "blueprint_fr": (
            "Está disponível uma versão francesa: [`aquamedic_alerts.fr.yaml`]"
            f"({BLUEPRINT_DIR}/aquamedic_alerts.fr.yaml)."
        ),
        "card": (
            "As tarefas aparecem também na vista de manutenção do "
            "[ha-reef-card](https://github.com/Elwinmage/ha-reef-card), ao lado "
            "das do Red Sea: ambas as integrações publicam o mesmo contrato de "
            "entidades `reef_role`."
        ),
        "pumps": {
            "drift": "EcoDrift / SmartDrift",
            "return": "DC Runner (retorno)",
            "skimmer": "DC Runner (escumador)",
        },
    },
}

# (pump group, task name per language, default, range) — mirrors maintenance.py.
ROWS: list[tuple[str, dict[str, str], str, str]] = [
    (
        "drift",
        {
            "en": "Clean impeller and filter basket",
            "fr": "Nettoyer le rotor et le panier de filtration",
            "de": "Rotor und Filterkorb reinigen",
            "es": "Limpiar el rotor y la cesta de filtración",
            "it": "Pulire il rotore e il cestello filtrante",
            "pl": "Wyczyść wirnik i kosz filtra",
            "pt": "Limpar o rotor e o cesto de filtragem",
        },
        "2",
        "1–3",
    ),
    (
        "drift",
        {
            "en": "Descale pump",
            "fr": "Détartrer la pompe",
            "de": "Pumpe entkalken",
            "es": "Descalcificar la bomba",
            "it": "Decalcificare la pompa",
            "pl": "Odkamień pompę",
            "pt": "Descalcificar a bomba",
        },
        "6",
        "3–9",
    ),
    (
        "drift",
        {
            "en": "Replace impeller and bearings",
            "fr": "Remplacer le rotor et les roulements",
            "de": "Rotor und Lager ersetzen",
            "es": "Sustituir el rotor y los rodamientos",
            "it": "Sostituire il rotore e i cuscinetti",
            "pl": "Wymień wirnik i łożyska",
            "pt": "Substituir o rotor e os rolamentos",
        },
        "18",
        "12–24",
    ),
    (
        "return",
        {
            "en": "Clean suction strainer",
            "fr": "Nettoyer la crépine d'aspiration",
            "de": "Ansaugkorb reinigen",
            "es": "Limpiar la cesta de aspiración",
            "it": "Pulire il cestello di aspirazione",
            "pl": "Wyczyść kosz ssawny",
            "pt": "Limpar o cesto de aspiração",
        },
        "6 w",
        "3–9 w",
    ),
    (
        "return",
        {
            "en": "Clean impeller and pump chamber",
            "fr": "Nettoyer le rotor et la chambre de pompe",
            "de": "Rotor und Pumpenkammer reinigen",
            "es": "Limpiar el rotor y la cámara de la bomba",
            "it": "Pulire il rotore e la camera della pompa",
            "pl": "Wyczyść wirnik i komorę pompy",
            "pt": "Limpar o rotor e a câmara da bomba",
        },
        "4",
        "2–6",
    ),
    (
        "return",
        {
            "en": "Replace impeller and bearings",
            "fr": "Remplacer le rotor et les roulements",
            "de": "Rotor und Lager ersetzen",
            "es": "Sustituir el rotor y los rodamientos",
            "it": "Sostituire il rotore e i cuscinetti",
            "pl": "Wymień wirnik i łożyska",
            "pt": "Substituir o rotor e os rolamentos",
        },
        "18",
        "12–24",
    ),
    (
        "skimmer",
        {
            "en": "Clean collection cup",
            "fr": "Nettoyer le gobelet",
            "de": "Schaumtopf reinigen",
            "es": "Limpiar el vaso colector",
            "it": "Pulire il bicchiere di raccolta",
            "pl": "Wyczyść kubek odpieniacza",
            "pt": "Limpar o copo coletor",
        },
        "2 w",
        "1–4 w",
    ),
    (
        "skimmer",
        {
            "en": "Clean venturi and air line",
            "fr": "Nettoyer le venturi et le tuyau d'air",
            "de": "Venturi und Luftschlauch reinigen",
            "es": "Limpiar el venturi y el tubo de aire",
            "it": "Pulire il venturi e il tubo dell'aria",
            "pl": "Wyczyść venturi i wężyk powietrza",
            "pt": "Limpar o venturi e o tubo de ar",
        },
        "4 w",
        "2–8 w",
    ),
    (
        "skimmer",
        {
            "en": "Clean needle wheel",
            "fr": "Nettoyer le rotor à aiguilles",
            "de": "Nadelrad reinigen",
            "es": "Limpiar el rotor de agujas",
            "it": "Pulire la girante ad aghi",
            "pl": "Wyczyść wirnik igiełkowy",
            "pt": "Limpar o rotor de agulhas",
        },
        "2",
        "1–4",
    ),
    (
        "skimmer",
        {
            "en": "Descale skimmer body",
            "fr": "Détartrer le corps de l'écumeur",
            "de": "Abschäumerkörper entkalken",
            "es": "Descalcificar el cuerpo del skimmer",
            "it": "Decalcificare il corpo dello schiumatoio",
            "pl": "Odkamień korpus odpieniacza",
            "pt": "Descalcificar o corpo do escumador",
        },
        "6",
        "3–12",
    ),
    (
        "skimmer",
        {
            "en": "Replace needle wheel and bearings",
            "fr": "Remplacer le rotor à aiguilles et les roulements",
            "de": "Nadelrad und Lager ersetzen",
            "es": "Sustituir el rotor de agujas y los rodamientos",
            "it": "Sostituire la girante ad aghi e i cuscinetti",
            "pl": "Wymień wirnik igiełkowy i łożyska",
            "pt": "Substituir o rotor de agulhas e os rolamentos",
        },
        "18",
        "12–24",
    ),
]

# "months unless stated" footnote, per language.
UNIT_NOTE: dict[str, str] = {
    "en": "Values in months unless followed by `w` (weeks). Aqua Medic "
    "publishes no numeric interval, so these defaults come from reef keeping "
    "practice — every one of them is adjustable per pump.",
    "fr": "Valeurs en mois sauf si suivies de `w` (semaines). Aqua Medic ne "
    "publie aucun intervalle chiffré : ces valeurs viennent de la pratique "
    "récifale et sont toutes ajustables pompe par pompe.",
    "de": "Werte in Monaten, außer mit `w` (Wochen). Aqua Medic nennt keine "
    "Zahlenwerte; diese Vorgaben stammen aus der Riffaquaristik-Praxis und "
    "sind alle pro Pumpe einstellbar.",
    "es": "Valores en meses salvo si van seguidos de `w` (semanas). Aqua Medic "
    "no publica ningún intervalo numérico: estos valores vienen de la práctica "
    "en acuarios de arrecife y son ajustables bomba por bomba.",
    "it": "Valori in mesi salvo se seguiti da `w` (settimane). Aqua Medic non "
    "pubblica alcun intervallo numerico: questi valori derivano dalla pratica "
    "in acquario di barriera e sono regolabili pompa per pompa.",
    "pl": "Wartości w miesiącach, chyba że z `w` (tygodnie). Aqua Medic nie "
    "podaje żadnych liczb: te wartości pochodzą z praktyki akwarystyki rafowej "
    "i można je zmienić dla każdej pompy.",
    "pt": "Valores em meses, exceto se seguidos de `w` (semanas). A Aqua Medic "
    "não publica qualquer intervalo numérico: estes valores vêm da prática em "
    "aquário de recife e são ajustáveis bomba a bomba.",
}


def build_section(lang: str) -> str:
    """Render the whole Maintenance section for one language."""
    t = TEXT[lang]
    pumps: dict[str, str] = t["pumps"]
    lines = [
        MARKER_START,
        "",
        f"## {t['title']}",
        "",
        t["intro"],
        "",
        t["role"],
        "",
        t["table_head"],
        "|---|---|---|---|",
    ]
    for group, names, default, span in ROWS:
        lines.append(f"| {pumps[group]} | {names[lang]} | {default} | {span} |")
    lines += [
        "",
        f"> {UNIT_NOTE[lang]}",
        "",
        f"### {t['blueprint_title']}",
        "",
        t["blueprint"],
        "",
        IMPORT_BADGE,
        "",
        t["blueprint_fr"],
        "",
        t["card"],
        "",
        MARKER_END,
        "",
        "",
    ]
    return "\n".join(lines)


def patch(path: str, lang: str, before: str) -> None:
    """Insert (or refresh) the section right before `before` in one README."""
    with open(path, encoding="utf-8") as fh:
        content = fh.read()

    if MARKER_START in content:
        head, rest = content.split(MARKER_START, 1)
        _, tail = rest.split(MARKER_END, 1)
        content = head + tail.lstrip("\n")

    if before not in content:
        raise SystemExit(f"{path}: heading {before!r} not found")

    content = content.replace(before, build_section(lang) + before, 1)

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"  patched {os.path.relpath(path, REPO_ROOT)}")


def main() -> None:
    for rel, (lang, before) in FILES.items():
        patch(os.path.join(REPO_ROOT, rel), lang, before)


if __name__ == "__main__":
    main()
