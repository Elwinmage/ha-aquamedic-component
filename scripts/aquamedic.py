import requests
import argparse
import uuid
import sys
import json
import os

# ── ANSI color helpers ────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"


def ok(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def warn(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def err(msg):
    print(f"{RED}❌ {msg}{RESET}")


def info(msg):
    print(f"{CYAN}🔎 {msg}{RESET}")


def step(msg):
    print(f"{BOLD}{msg}{RESET}")


# ── Identifiants confirmés ────────────────────────────────────────────────────
APP_ID = "07452c4f036a4be3acedf8dbeef38320"
REAL_BASE_URL = "https://euapi.gizwits.com/app"


def build_urls(base: str) -> dict:
    """Return all API URLs derived from a base URL (real cloud or simulator)."""
    b = base.rstrip("/")
    return {
        "provision": f"{b}/provision",
        "login": f"{b}/login",
        "bindings": f"{b}/bindings",
        "devdata": f"{b}/devdata/{{device_id}}/latest",
        "datapoint": f"{b}/datapoint",
    }


def get_headers(token=None):
    """Build common request headers, optionally with user token."""
    h = {
        "X-Gizwits-Application-Id": APP_ID,
        "Content-Type": "application/json",
        "User-Agent": "gizwitssuperapprn/154300000 CFNetwork/3826.500.131 Darwin/24.5.0",
    }
    if token:
        h["X-Gizwits-User-token"] = token
    return h


def provision(session, phone_id, urls):
    """Provision a virtual mobile client — required before login."""
    step(f"Provisioning du client (Phone ID: {phone_id[:8]}...)...")
    res = session.post(
        urls["provision"],
        headers=get_headers(),
        json={
            "phone_id": phone_id,
            "os": "Linux",
            "os_ver": "5.4",
            "sdk_version": "2.23.23.01613",
            "phone_model": "Python-Client",
        },
    )
    if res.status_code == 200:
        ok("Provisioning reussi.")
    else:
        warn(f"Provisioning ignore ou echoue ({res.status_code})")


def login(session, username, password, urls):
    """Authenticate and return token."""
    step(f"Connexion pour {username}...")
    res = session.post(
        urls["login"],
        headers=get_headers(),
        json={"username": username, "password": password},
    )
    if res.status_code != 200:
        err(f"Erreur Login: {res.text}")
        return None
    token = res.json().get("token")
    ok("Authentifie! Token recupere.")
    return token


def get_devices(session, token, urls):
    """Fetch all devices bound to the account."""
    info("Recuperation des appareils via /bindings...")
    res = session.get(
        f"{urls['bindings']}?limit=20",
        headers=get_headers(token),
    )
    if res.status_code != 200:
        err(f"Erreur Bindings ({res.status_code}): {res.text}")
        return []
    return res.json().get("devices", [])


def get_device_latest(session, token, device_id, urls):
    """Fetch latest reported attribute values for a device."""
    url = urls["devdata"].format(device_id=device_id)
    res = session.get(url, headers=get_headers(token))
    if res.status_code == 200:
        return res.json()
    warn(f"Impossible de recuperer l'etat ({res.status_code}): {res.text}")
    return None


def get_datapoints(session, token, product_key, urls):
    """Fetch the datapoint schema for a given product_key."""
    res = session.get(
        urls["datapoint"],
        headers=get_headers(token),
        params={"product_key": product_key},
    )
    if res.status_code == 200:
        return res.json()
    warn(f"Datapoints non disponibles ({res.status_code}): {res.text}")
    return None


def save_datapoints(device, schema, output_dir):
    """Save the raw datapoint schema to a JSON file in output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    name = device.get("dev_alias") or device.get("product_name") or "unknown"
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    product_key = device.get("product_key", "unknown")
    filename = f"{safe_name}_{product_key}.json"
    filepath = os.path.join(output_dir, filename)

    payload = {
        "device": {
            "dev_alias": device.get("dev_alias"),
            "product_name": device.get("product_name"),
            "did": device.get("did"),
            "product_key": product_key,
            "is_online": device.get("is_online"),
        },
        "datapoints": schema,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    ok(f"Datapoints sauvegardes -> {filepath}")


def describe_datapoint(dp):
    """Return a human-readable one-liner for a single datapoint."""
    name = dp.get("name", "?")
    display = dp.get("display_name", name)
    rw_raw = dp.get("rw", "?")
    rw = "R/W" if rw_raw == "rw" else ("R" if rw_raw == "ro" else "W")
    dp_type = dp.get("type", "?")
    unit = dp.get("unit", "")

    extra = ""
    if dp_type == "enum":
        extra = f"  valeurs : {dp.get('enum', [])}"
    elif dp_type in ("uint8", "uint16", "uint32", "int8", "int16", "int32"):
        lo, hi = dp.get("min", "?"), dp.get("max", "?")
        extra = f"  range : {lo}-{hi}{(' ' + unit) if unit else ''}"
    elif dp_type == "bool":
        extra = "  valeurs : 0 (off) / 1 (on)"

    rw_color = GREEN if "W" in rw else DIM
    return (
        f"    {rw_color}[{rw}]{RESET} "
        f"{BOLD}{display}{RESET} "
        f"{DIM}(attr: {name}, type: {dp_type}){RESET}"
        f"{CYAN}{extra}{RESET}"
    )


def print_device_info(session, token, device, urls, save_dir=None):
    """Print full info for one device: metadata, live state and datapoints."""
    name = device.get("dev_alias") or device.get("product_name") or "Inconnu"
    did = device.get("did", "?")
    product_key = device.get("product_key", "")
    is_online = device.get("is_online", False)
    status_str = f"{GREEN}ONLINE{RESET}" if is_online else f"{RED}OFFLINE{RESET}"

    print("=" * 60)
    print(f"{BOLD}Nom    :{RESET} {name}")
    print(f"{BOLD}ID     :{RESET} {did}")
    print(f"{BOLD}PK     :{RESET} {DIM}{product_key}{RESET}")
    print(f"{BOLD}Statut :{RESET} {status_str}")

    # Current state
    latest = get_device_latest(session, token, did, urls)
    if latest:
        attrs = latest.get("attr", {})
        updated = latest.get("updated_at", "?")
        print(f"\n  {CYAN}Etat actuel{RESET} {DIM}(mis a jour : {updated}){RESET}")
        if attrs:
            for key, val in attrs.items():
                print(f"    {BOLD}{key}{RESET} = {GREEN}{val}{RESET}")
        else:
            print(f"    {DIM}(aucune donnee disponible){RESET}")

    # Datapoint schema
    schema = None
    if product_key:
        print(f"\n  {CYAN}Datapoints supportes{RESET}")
        schema = get_datapoints(session, token, product_key, urls)
        if schema:
            entities = schema.get("entities", [])
            dps = []
            for entity in entities:
                dps.extend(entity.get("attrs", []))
            if dps:
                for dp in dps:
                    print(describe_datapoint(dp))
            else:
                warn("Structure inattendue - dump brut :")
                print(json.dumps(schema, indent=4, ensure_ascii=False))
        else:
            print(f"    {DIM}(datapoints non accessibles pour ce produit){RESET}")

    # Save JSON
    if save_dir is not None and schema is not None:
        save_datapoints(device, schema, save_dir)

    print("-" * 60)


def get_gizwits_devices(username, password, urls, save_dir=None):
    session = requests.Session()
    phone_id = str(uuid.uuid4()).upper()

    try:
        provision(session, phone_id, urls)
        token = login(session, username, password, urls)
        if not token:
            return

        devices = get_devices(session, token, urls)
        if not devices:
            print(f"{YELLOW}Aucun appareil trouve.{RESET}")
            return

        print(f"\n{BOLD}{len(devices)} appareil(s) trouve(s) :{RESET}\n")
        for d in devices:
            print_device_info(session, token, d, urls, save_dir=save_dir)

    except Exception as e:
        err(f"Erreur systeme : {e}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_output = os.path.join(script_dir, "devices_datapoints")

    parser = argparse.ArgumentParser(
        description="Gizwits Device Explorer -- Aqua Medic / SmartDrift",
        epilog=(
            "Exemples :\n"
            "  python aquamedic.py user@mail.com mdp\n"
            "  python aquamedic.py user@mail.com mdp --sim\n"
            "  python aquamedic.py user@mail.com mdp --sim --sim-url http://192.168.100.10:8080\n"
            "  python aquamedic.py user@mail.com mdp --save\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("username", help="Email Gizwits / Aqua Medic")
    parser.add_argument("password", help="Mot de passe")

    # Simulator options
    sim_group = parser.add_argument_group("simulateur")
    sim_group.add_argument(
        "--sim",
        action="store_true",
        help="Se connecter au simulateur local au lieu du cloud Gizwits",
    )
    sim_group.add_argument(
        "--sim-url",
        default="http://localhost:8080",
        metavar="URL",
        help="URL de base du simulateur (defaut : http://localhost:8080)",
    )

    # Save options
    save_group = parser.add_argument_group("sauvegarde")
    save_group.add_argument(
        "--save",
        action="store_true",
        help=f"Enregistre les datapoints JSON dans {default_output}/",
    )
    save_group.add_argument(
        "--output-dir",
        default=default_output,
        metavar="DIR",
        help=f"Dossier de sortie pour --save (defaut : {default_output})",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Build URL map: simulator or real cloud
    if args.sim:
        # Ensure /app suffix is present and strip trailing slash
        base = args.sim_url.rstrip("/")
        api_base = base if base.endswith("/app") else f"{base}/app"
        urls = build_urls(api_base)
        print(f"\n{YELLOW}[SIM] Mode simulateur -> {api_base}{RESET}\n")
    else:
        urls = build_urls(REAL_BASE_URL)

    save_dir = args.output_dir if args.save else None
    get_gizwits_devices(args.username, args.password, urls, save_dir=save_dir)
