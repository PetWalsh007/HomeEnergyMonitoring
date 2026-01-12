import time
import requests
from requests.auth import HTTPDigestAuth


TOKENS_PATH = "output/auth/tokens.txt"
DEFAULT_BASE_URL = "https://s18.myenergi.net"


def load_tokens(path: str) -> dict:
    tokens = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            tokens[k.strip()] = v.strip()
    return tokens


def fetch_eddi_snapshot(base_url: str, hub_serial: str, api_key: str) -> dict:
    url = f"{base_url.rstrip('/')}/cgi-jstatus-E"
    r = requests.get(url, auth=HTTPDigestAuth(hub_serial, api_key), timeout=10)
    r.raise_for_status()
    return r.json()["eddi"][0]


def compute_metrics(eddi0: dict) -> dict:
    grid = int(eddi0.get("ectp2", 0))   # +import, -export
    gen = int(eddi0.get("ectp3", 0))    # negative when generating
    divert = int(eddi0.get("div", 0))   # W

    grid_import = max(grid, 0)
    grid_export = max(-grid, 0)
    solar = abs(gen)

    house = solar + grid_import - grid_export - divert

    return {
        "grid_import_w": grid_import,
        "grid_export_w": grid_export,
        "solar_w": solar,
        "divert_w": divert,
        "house_w": house,
    }


def w_to_kwh(power_w: float, dt_seconds: float) -> float:
    return power_w * dt_seconds / 3_600_000


def format_row(ts: str, m: dict) -> str:
    return (
        f"{ts} | "
        f"Import {m['grid_import_w']:>5} W | "
        f"Export {m['grid_export_w']:>5} W | "
        f"Solar {m['solar_w']:>5} W | "
        f"Divert {m['divert_w']:>5} W | "
        f"House {m['house_w']:>5} W"
    )


def run_test(base_url: str, hub_serial: str, api_key: str,
             poll_seconds: int = 30, duration_seconds: int = 180) -> None:

    print(f"Polling every {poll_seconds}s for ~{duration_seconds}s")
    print("-" * 90)

    totals = {
        "grid_import_kwh": 0.0,
        "grid_export_kwh": 0.0,
        "solar_kwh": 0.0,
        "divert_kwh": 0.0,
        "house_kwh": 0.0,
    }

    t_prev = time.time()
    t_end = t_prev + duration_seconds

    while True:
        t_now = time.time()
        dt = t_now - t_prev
        t_prev = t_now

        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        eddi0 = fetch_eddi_snapshot(base_url, hub_serial, api_key)
        m = compute_metrics(eddi0)

        print(format_row(ts, m))

        # integrate energy
        totals["grid_import_kwh"] += w_to_kwh(m["grid_import_w"], dt)
        totals["grid_export_kwh"] += w_to_kwh(m["grid_export_w"], dt)
        totals["solar_kwh"] += w_to_kwh(m["solar_w"], dt)
        totals["divert_kwh"] += w_to_kwh(m["divert_w"], dt)
        totals["house_kwh"] += w_to_kwh(m["house_w"], dt)

        if time.time() >= t_end:
            break

        time.sleep(poll_seconds)

    print("-" * 90)
    print("Totals over test window:")
    print(f"  Grid import : {totals['grid_import_kwh']:.4f} kWh")
    print(f"  Grid export : {totals['grid_export_kwh']:.4f} kWh")
    print(f"  Solar gen   : {totals['solar_kwh']:.4f} kWh")
    print(f"  Eddi divert : {totals['divert_kwh']:.4f} kWh")
    print(f"  House load  : {totals['house_kwh']:.4f} kWh")


def main():
    tokens = load_tokens(TOKENS_PATH)
    hub = tokens["HUB_SERIAL"]
    key = tokens["API_KEY"]
    base = tokens.get("BASE_URL", DEFAULT_BASE_URL)

    run_test(base, hub, key, poll_seconds=60, duration_seconds=180)


if __name__ == "__main__":
    main()
