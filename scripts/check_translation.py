#!/usr/bin/env python3
"""Verify that all entity keys defined in const.py have translations."""
import json
import os
import re
import sys

from colorama import Fore, Style

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
base_path = os.path.join(repo_root, "custom_components", "aquamedic")

const_file = os.path.join(base_path, "const.py")
translations_path = os.path.join(base_path, "translations")
strings_file = os.path.join(base_path, "strings.json")

# TODO: implement translation key checks for your integration
print(Fore.GREEN + "Translation check passed (stub)" + Style.RESET_ALL)
sys.exit(0)
