#!/usr/bin/env python3
"""
EmashCo API uploader for hardware detection.

Posts a detected laptop to the EmashCo backend's intake endpoint
(``POST /api/v2/intake/model``), which creates the model, hardware data, the
default variant, the inventory row and the manual fields in ONE atomic,
race-safe transaction.

Replaces the old direct-to-Supabase uploader: the platform moved off Supabase
onto PostgreSQL (CNPG), and Supabase is read-only/retired. Nothing here talks to
a database — the backend owns all schema knowledge, deduplication and validation.

secrets.json (on the USB stick):

    {"api_key": "<intake key>"}

The backend URL is hardcoded (DEFAULT_API_URL) so sticks carry only the secret;
an "api_url" entry still overrides it for staging/testing. For backward
compatibility the key is also read from the legacy "supabase_anon_key" entry, so
sticks issued before the PostgreSQL migration keep working untouched.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import json
import time

import requests

# Hardcoded so a stick only has to carry the secret. secrets.json "api_url" overrides
# it (staging/local testing).
DEFAULT_API_URL = "https://bbapi.anew-tech.com"

# Generous: the intake call runs one transaction plus dedup, and technicians are
# often on slow shop wifi. Still bounded so a hung network can't hang the tool.
REQUEST_TIMEOUT_SECONDS = 60
INTAKE_PATH = "/api/v2/intake/model"

# Shop wifi drops connections. Retrying is safe: the endpoint dedups the model under an
# advisory lock, so a POST that committed before we gave up comes back as status="exists"
# on the retry rather than creating a duplicate.
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3

# Fields the API validates as strictly positive (gt=0 / ge=1). A detected 0 means the probe
# failed (e.g. lscpu printing "CPU max MHz: 0.0000" in a VM), so send nothing rather than
# let one unreadable value 422 the entire scan.
_POSITIVE_ONLY = ("cpu_cores", "cpu_max_ghz", "cpu_speed_ghz", "screen_size_inches")

# Detector storage_controller_type -> the canonical interface the API accepts, which matches
# the operator's Zoho item names ("256-NVMe", "256-2.5"). Anything unmapped is sent as absent
# so the operator can set it per model in the UI rather than us guessing.
_STORAGE_INTERFACE = {
    "NVMe": "NVMe",
    "SATA": "2.5",
    "SATA (AHCI)": "2.5",
    "eMMC": "eMMC",
}

# Where the intake key may live, in priority order. "supabase_anon_key" is the
# pre-migration entry: the same secret was re-issued as the intake key, so sticks
# that were never re-imaged keep working with no edit at all.
_KEY_FIELDS = ("api_key", "supabase_anon_key")


class UploadError(RuntimeError):
    """Raised when the backend rejects the upload or is unreachable."""


def load_secrets(secrets_path: str = "secrets.json") -> Dict[str, Any]:
    """Load secrets and normalize them to ``api_url`` + ``api_key``.

    The key is taken from ``api_key``, falling back to the pre-migration
    ``supabase_anon_key`` (the same secret was re-issued as the intake key, so an
    un-reimaged stick still works). The URL defaults to :data:`DEFAULT_API_URL`.

    Raises:
        FileNotFoundError: secrets file missing
        ValueError: no usable key in the file
    """
    secrets_file = Path(secrets_path)
    if not secrets_file.exists():
        raise FileNotFoundError(f"Secrets file not found: {secrets_path}")

    with open(secrets_file, "r") as f:
        secrets = json.load(f)

    source = next((f for f in _KEY_FIELDS if str(secrets.get(f) or "").strip()), None)
    if source is None:
        raise ValueError(
            f"No API key in {secrets_path}: expected an 'api_key' entry "
            f"(or the legacy '{_KEY_FIELDS[1]}'). See secrets.json.example."
        )

    # Normalize so the rest of the module only reads these two.
    secrets["api_key"] = str(secrets[source]).strip()
    secrets["api_url"] = str(secrets.get("api_url") or DEFAULT_API_URL).rstrip("/")

    if source != "api_key":
        print(
            f"ℹ️  Using the legacy '{source}' entry as the API key. This still works; "
            "ask your admin for an updated secrets.json when convenient."
        )

    return secrets


def _clean(value: Optional[str]) -> Optional[str]:
    """Normalize a detected string: strip, and treat blank as absent."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_payload(
    raw_data: Dict[str, Any], bestbuy_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Map detector output onto the intake endpoint's request body.

    GPU model extraction is deliberately NOT done here — the backend derives
    integrated/dedicated GPU from ``integrated_gpu_model``/``dedicated_gpu_model``
    with a fallback to the raw ``gpus``/``gpu_type`` fields, so both paths (UI and
    USB) share one implementation.
    """
    # raw_data is authoritative: prompt_manual_fields() writes the technician's answer there,
    # while the bestbuy_data mirror was built by map_to_bestbuy_fields() BEFORE the prompt ran.
    # This matters beyond one column — has_touchscreen is part of the model dedup tuple.
    if raw_data.get("has_touchscreen") is not None:
        has_touchscreen = bool(raw_data["has_touchscreen"])
    else:
        has_touchscreen = (
            bestbuy_data.get("_TouchscreenDisplay_23335_CAT_1002_EN") == "Yes"
        )

    hardware_data: Dict[str, Any] = {
        # Required by the API
        "brand": _clean(raw_data.get("brand")) or "Unknown",
        "model": _clean(raw_data.get("model")) or "Unknown Model",
        "cpu_model": _clean(raw_data.get("cpu_model")) or "Unknown CPU",
        "ram_size_gb": int(raw_data.get("ram_size_gb") or 0),
        # Optional
        "family": _clean(raw_data.get("family")),
        "manufacturer_sku": _clean(raw_data.get("sku")),
        "cpu_cores": raw_data.get("cpu_cores"),
        "cpu_max_ghz": raw_data.get("cpu_max_ghz"),
        "cpu_speed_ghz": raw_data.get("cpu_speed_ghz"),
        "cpu_l3_cache": _clean(raw_data.get("cpu_l3_cache")),
        "ram_type": _clean(raw_data.get("ram_type")),
        "ssd_capacity_gb": raw_data.get("ssd_capacity_gb"),
        "storage_interface": _STORAGE_INTERFACE.get(
            _clean(raw_data.get("storage_controller_type")) or ""
        ),
        "screen_size_inches": raw_data.get("screen_size_inches"),
        "screen_resolution": _clean(raw_data.get("screen_resolution")),
        "integrated_gpu_model": _clean(raw_data.get("integrated_gpu_model")),
        "dedicated_gpu_model": _clean(raw_data.get("dedicated_gpu_model")),
        "gpus": raw_data.get("gpus"),
        "gpu_type": _clean(raw_data.get("gpu_type")),
        "has_wifi": bool(raw_data.get("has_wifi", False)),
        "has_bluetooth": bool(raw_data.get("has_bluetooth", False)),
        "has_ethernet": bool(raw_data.get("has_ethernet", False)),
        "has_webcam": bool(raw_data.get("has_webcam", False)),
        # Full dump, kept verbatim for later reference
        "raw_detection_json": raw_data,
    }

    manual_fields: Dict[str, Any] = {
        "has_touchscreen": has_touchscreen,
        "keyboard_language": _clean(
            bestbuy_data.get("_KeyboardLanguage_24678_CAT_1002_EN")
        ),
        "backlit_keyboard": bestbuy_data.get("_BacklitKeyboard_24680_CAT_1002_EN")
        == "Yes",
        "convertible_hybrid": bestbuy_data.get(
            "_ConvertibleHybridDisplay_36185_CAT_1002_EN"
        )
        == "Yes",
        "colour": _clean(bestbuy_data.get("_Colour_5105_CAT_1002_EN")),
        "product_condition": _clean(
            bestbuy_data.get("_ProductCondition_20257570_CAT_1002_EN")
        ),
    }

    # Drop unset optionals so the API applies its own defaults rather than storing explicit
    # nulls over them. A detected 0 counts as unset for the positive-only fields (see above).
    # Note `is not None`, not truthiness: False and 0 are meaningful answers elsewhere.
    hardware_data = {
        k: v
        for k, v in hardware_data.items()
        if v is not None and not (k in _POSITIVE_ONLY and v <= 0)
    }
    manual_fields = {k: v for k, v in manual_fields.items() if v is not None}

    return {"hardware_data": hardware_data, "manual_fields": manual_fields}


def _describe_error(response: requests.Response) -> str:
    """Turn a failed response into something a technician can act on."""
    if response.status_code == 401:
        return "Rejected (401): the api_key in secrets.json is missing or wrong."
    if response.status_code == 503:
        return "Rejected (503): intake is not configured on the server — contact the admin."
    if response.status_code == 422:
        try:
            details = response.json().get("detail", [])
            fields = "; ".join(
                f"{'.'.join(str(p) for p in d.get('loc', []))}: {d.get('msg', '')}"
                for d in details
            ) or response.text[:300]
        except (ValueError, AttributeError, TypeError):
            fields = response.text[:300]
        return f"Rejected (422) — detected data failed validation: {fields}"
    try:
        body = response.json()
        detail = body.get("detail") if isinstance(body, dict) else None
    except ValueError:
        detail = None
    return f"Upload failed ({response.status_code}): {detail or response.text[:300]}"


def upload_to_database(
    secrets: Dict[str, Any], raw_data: Dict[str, Any], bestbuy_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Upload a detected laptop to the EmashCo API.

    Returns the intake response: ``{model_id, variant_id, shop_sku, status, message}``
    where status is ``"created"`` or ``"exists"``.

    Raises:
        UploadError: on a network failure or a non-2xx response
    """
    print("\n" + "=" * 60)
    print("📤 Uploading to EmashCo API")
    print("=" * 60 + "\n")

    base_url = str(secrets.get("api_url") or DEFAULT_API_URL).rstrip("/")
    url = f"{base_url}{INTAKE_PATH}"
    payload = build_payload(raw_data, bestbuy_data)

    hw = payload["hardware_data"]
    print(f"🖥️  {hw.get('brand')} {hw.get('model')}")
    print(f"    {hw.get('cpu_model')}")
    print(f"    {hw.get('ram_size_gb')}GB RAM / {hw.get('ssd_capacity_gb', 0)}GB SSD")
    print(f"\n🌐 POST {url}")

    headers = {
        "X-API-Key": secrets["api_key"],
        "Content-Type": "application/json",
    }
    response = None
    last_error = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
                # requests only strips Authorization across a host change, NOT custom headers:
                # a captive portal's 302 would be handed the intake key. api_url is fixed, so
                # there is no legitimate redirect to follow.
                allow_redirects=False,
            )
        except requests.exceptions.Timeout:
            last_error = f"Timed out after {REQUEST_TIMEOUT_SECONDS}s contacting {base_url}"
            response = None
        except requests.exceptions.ConnectionError:
            last_error = f"Could not reach {base_url}"
            response = None
        else:
            if response.status_code < 500:
                break
            last_error = _describe_error(response)
            response = None

        if attempt < MAX_ATTEMPTS:
            delay = RETRY_BACKOFF_SECONDS * attempt
            print(f"⚠️  {last_error} — retrying in {delay}s ({attempt}/{MAX_ATTEMPTS})")
            time.sleep(delay)

    if response is None:
        raise UploadError(
            f"{last_error}. Gave up after {MAX_ATTEMPTS} attempts — check the internet "
            "connection and that api_url in secrets.json is correct."
        )

    if 300 <= response.status_code < 400:
        raise UploadError(
            f"Server redirected to {response.headers.get('Location')!r} — refusing to resend "
            "the API key. Check api_url, and whether this wifi has a login page."
        )

    if not response.ok:
        raise UploadError(_describe_error(response))

    try:
        result = response.json()
    except ValueError as e:
        raise UploadError(
            f"Server returned a non-JSON response ({response.status_code})."
        ) from e

    print("\n" + "=" * 60)
    print("✅ Upload Complete!")
    print("=" * 60 + "\n")

    return result
