import os
from pathlib import Path

from dotenv import load_dotenv


CONFIG_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CONFIG_DIR.parent

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(CONFIG_DIR / ".env")

AGMARKNET_API_KEY = (
    os.getenv("AGMARKNET_API_KEY")
    or os.getenv("AGMARKET_API_KEY")
    or os.getenv("DATA_GOV_API_KEY")
)
AGMARKNET_RESOURCE_ID = os.getenv(
    "AGMARKNET_RESOURCE_ID",
    "9ef84268-d588-465a-a308-a864a43d0070",
)
AGMARKNET_BASE_URL = os.getenv(
    "AGMARKNET_BASE_URL",
    "https://api.data.gov.in/resource",
)
TRANSPORT_COST_PER_KM = float(os.getenv("TRANSPORT_COST_PER_KM", "35"))
MANDI_NET_GAIN_THRESHOLD = float(os.getenv("MANDI_NET_GAIN_THRESHOLD", "500"))
EXPECTED_QUINTALS_PER_ACRE = float(os.getenv("EXPECTED_QUINTALS_PER_ACRE", "10"))
