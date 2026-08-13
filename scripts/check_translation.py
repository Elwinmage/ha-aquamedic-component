#!/usr/bin/env python3
"""Verify that every entity translation key is present in every locale.

Expected keys are discovered from the source, never hardcoded:

- Static entities: any literal ``translation_key="..."`` found in a platform
  module (button.py, number.py, select.py, switch.py, binary_sensor.py). The
  file name gives the platform section of ``entity``.
- Maintenance entities: their keys are built at runtime from the catalogue
  (``maint_<task>``, ``maint_<task>_interval_<unit>``, ``maint_<task>_notify``)
  so they are derived from the ``MaintenanceTask`` definitions in
  maintenance.py instead.
- Pump role select: options come from ``PUMP_ROLE_OPTIONS``.

The modules are parsed with ``ast``: the pre-commit hook environment has no
Home Assistant, so importing them is not an option.
"""

from __future__ import annotations

import ast
import json
import os
import sys

from colorama import Fore, Style

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_PATH = os.path.join(REPO_ROOT, "custom_components", "aquamedic")
TRANSLATIONS_PATH = os.path.join(BASE_PATH, "translations")
STRINGS_FILE = os.path.join(BASE_PATH, "strings.json")
MAINTENANCE_FILE = os.path.join(BASE_PATH, "maintenance.py")

# Platform module -> `entity` section in the translation files.
PLATFORM_FILES = {
    "binary_sensor.py": "binary_sensor",
    "button.py": "button",
    "number.py": "number",
    "select.py": "select",
    "switch.py": "switch",
}


def _parse(path: str) -> ast.Module:
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def literal_translation_keys(path: str) -> set[str]:
    """Return every literal translation key declared in a module.

    Covers both flavours used in this integration: the ``translation_key=...``
    argument of an EntityDescription, and the ``_attr_translation_key = "..."``
    class attribute used by entities that have no description.
    """
    keys: set[str] = set()
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if (
                    kw.arg == "translation_key"
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, str)
                ):
                    keys.add(kw.value.value)
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if not isinstance(node.value.value, str):
                continue
            for target in node.targets:
                name = getattr(target, "id", None) or getattr(target, "attr", None)
                if name == "_attr_translation_key":
                    keys.add(node.value.value)
    return keys


def module_str_constants(tree: ast.Module) -> dict[str, str]:
    """Map module-level NAME = "value" assignments (annotated or not)."""
    consts: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.Assign):
            targets = node.targets
        else:
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(
            node.value.value, str
        ):
            continue
        for target in targets:
            name = getattr(target, "id", None)
            if name:
                consts[name] = node.value.value
    return consts


def maintenance_tasks() -> list[tuple[str, str]]:
    """Return [(translation_key, unit)] for every MaintenanceTask defined."""
    tasks: list[tuple[str, str]] = []
    for node in ast.walk(_parse(MAINTENANCE_FILE)):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name != "MaintenanceTask":
            continue
        fields = {
            kw.arg: kw.value.value
            for kw in node.keywords
            if isinstance(kw.value, ast.Constant)
        }
        tk = fields.get("translation_key")
        if isinstance(tk, str):
            # `unit` defaults to "weeks" on the dataclass.
            unit = fields.get("unit")
            tasks.append((tk, unit if isinstance(unit, str) else "weeks"))
    return tasks


def pump_role_options() -> list[str]:
    """Return the options of the pump_role select, from maintenance.py.

    The tuple lists PUMP_ROLE_* constants rather than raw strings, so the
    module-level constants are resolved first.
    """
    tree = _parse(MAINTENANCE_FILE)
    consts = module_str_constants(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if getattr(node.target, "id", None) != "PUMP_ROLE_OPTIONS":
            continue
        if not isinstance(node.value, ast.Tuple):
            continue
        options: list[str] = []
        for el in node.value.elts:
            if isinstance(el, ast.Constant) and isinstance(el.value, str):
                options.append(el.value)
            elif isinstance(el, ast.Name) and el.id in consts:
                options.append(consts[el.id])
        return options
    return []


def expected_keys() -> dict[str, set[str]]:
    """Build the full {platform: {translation_key}} expectation."""
    expected: dict[str, set[str]] = {
        section: set() for section in PLATFORM_FILES.values()
    }

    for filename, section in PLATFORM_FILES.items():
        path = os.path.join(BASE_PATH, filename)
        if os.path.exists(path):
            expected[section] |= literal_translation_keys(path)

    for tk, unit in maintenance_tasks():
        expected["button"].add(tk)
        expected["number"].add(f"{tk}_interval_{unit}")
        expected["switch"].add(f"{tk}_notify")

    return expected


def check_file(path: str, expected: dict[str, set[str]], states: list[str]) -> int:
    """Report missing keys in one translation file; return the error count."""
    rel = os.path.relpath(path, REPO_ROOT)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    entity = data.get("entity", {})
    errors = 0

    for section, keys in sorted(expected.items()):
        present = entity.get(section, {})
        for key in sorted(keys):
            payload = present.get(key)
            if payload is None:
                print(
                    f"{Fore.RED}  MISSING {rel}: entity.{section}.{key}{Style.RESET_ALL}"
                )
                errors += 1
            elif not payload.get("name"):
                print(
                    f"{Fore.RED}  NO NAME {rel}: entity.{section}.{key}{Style.RESET_ALL}"
                )
                errors += 1

    # The pump_role select must translate each of its options.
    role = entity.get("select", {}).get("pump_role", {}).get("state", {})
    for option in states:
        if option not in role:
            print(
                f"{Fore.RED}  MISSING {rel}: "
                f"entity.select.pump_role.state.{option}{Style.RESET_ALL}"
            )
            errors += 1

    # Unexpected keys are reported but never fail the hook: a key may be kept
    # around on purpose after an entity was removed.
    for section, present in entity.items():
        unknown = set(present) - expected.get(section, set())
        for key in sorted(unknown):
            print(
                f"{Fore.YELLOW}  ORPHAN  {rel}: entity.{section}.{key}{Style.RESET_ALL}"
            )

    return errors


def main() -> int:
    expected = expected_keys()
    states = pump_role_options()
    total = sum(len(keys) for keys in expected.values())
    print(f"Checking {total} entity translation key(s) + {len(states)} pump role(s)")

    files = [
        os.path.join(TRANSLATIONS_PATH, name)
        for name in sorted(os.listdir(TRANSLATIONS_PATH))
        if name.endswith(".json")
    ]
    if os.path.exists(STRINGS_FILE):
        files.append(STRINGS_FILE)

    errors = sum(check_file(path, expected, states) for path in files)

    if errors:
        print(f"{Fore.RED}Translation check failed: {errors} error(s){Style.RESET_ALL}")
        return 1
    print(f"{Fore.GREEN}Translation check passed{Style.RESET_ALL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
