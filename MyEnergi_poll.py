import requests
from requests.auth import HTTPDigestAuth
import json






r = requests.get(
    f"{BASE}/cgi-jstatus-E",
    auth=HTTPDigestAuth(HUB_SERIAL, API_KEY),
    timeout=10
)
r.raise_for_status()

e = r.json()["eddi"][0]

# Raw values
grid = e["ectp2"]        
gen  = e["ectp3"]        
div  = e["div"]          


grid_import = max(grid, 0)
grid_export = max(-grid, 0)
solar = abs(gen)
house = solar + grid_import - grid_export - div

print(f"Grid import : {grid_import} W")
print(f"Grid export : {grid_export} W")
print(f"Solar gen   : {solar} W")
print(f"Eddi divert : {div} W")
print(f"House load : {house} W")