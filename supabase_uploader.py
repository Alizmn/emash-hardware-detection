#!/usr/bin/env python3
"""
Supabase Database Uploader for Hardware Detection
Uploads laptop hardware data to Supabase database
"""

from supabase import create_client, Client
from typing import Dict, Any, Optional
from pathlib import Path
import json
import re


def load_secrets(secrets_path: str = "secrets.json") -> Dict[str, Any]:
    """
    Load secrets from JSON file.

    Args:
        secrets_path: Path to secrets JSON file

    Returns:
        Dictionary containing secrets

    Raises:
        FileNotFoundError: If secrets file doesn't exist
        ValueError: If required secrets are missing
    """
    secrets_file = Path(secrets_path)
    if not secrets_file.exists():
        raise FileNotFoundError(f"Secrets file not found: {secrets_path}")

    with open(secrets_file, 'r') as f:
        secrets = json.load(f)

    # Validate required fields
    required = ['supabase_url', 'supabase_anon_key']
    missing = [k for k in required if k not in secrets]
    if missing:
        raise ValueError(f"Missing required secrets: {', '.join(missing)}")

    return secrets


def create_supabase_client(secrets: Dict[str, Any]) -> Client:
    """
    Initialize and return authenticated Supabase client.

    Args:
        secrets: Dictionary containing supabase_url, supabase_anon_key, and optional clerk_token

    Returns:
        Authenticated Supabase client
    """
    url = secrets['supabase_url']
    key = secrets['supabase_anon_key']

    # Create client
    # Note: Python Supabase SDK doesn't support custom headers in the same way as JS
    # The Clerk token would need to be added per-request if required
    # For now, using anon key directly (RLS policies should be configured to allow this)
    client = create_client(url, key)

    # If Clerk token is provided, we could add it to headers for each request
    # but the Python SDK doesn't have a global headers option like the JS SDK
    # This would require modifying each query, which is complex
    # Alternative: Use Supabase service role key in secrets.json for this script

    return client


def extract_integrated_gpu(raw_data: Dict[str, Any]) -> Optional[str]:
    """Extract integrated GPU model from raw detection data"""
    # First, try to use the gpu_model that hardware_detector already parsed correctly
    if "gpu_model" in raw_data and raw_data.get("gpu_type") == "Integrated GPU":
        return raw_data["gpu_model"]

    # Fallback: Check if GPUs list exists and parse manually
    if "gpus" in raw_data and raw_data["gpus"]:
        for gpu_line in raw_data["gpus"]:
            # Look for Intel integrated graphics
            if "intel" in gpu_line.lower() and (
                "uhd" in gpu_line.lower()
                or "iris" in gpu_line.lower()
                or "hd graphics" in gpu_line.lower()
            ):
                # Extract GPU name from brackets if present
                bracket_match = re.search(r'\[(.+?)\]', gpu_line)
                if bracket_match:
                    return f"Intel {bracket_match.group(1)}"
                # Otherwise extract everything after controller type
                parts = gpu_line.split("controller:")
                if len(parts) > 1:
                    return parts[1].strip().split("(")[0].strip()
            # Look for AMD integrated graphics
            if (
                "amd" in gpu_line.lower()
                and "radeon" in gpu_line.lower()
                and "vega" in gpu_line.lower()
            ):
                # Extract GPU name from brackets if present
                bracket_match = re.search(r'\[(.+?)\]', gpu_line)
                if bracket_match:
                    return f"AMD {bracket_match.group(1)}"
                parts = gpu_line.split("controller:")
                if len(parts) > 1:
                    return parts[1].strip().split("(")[0].strip()

    return None


def extract_dedicated_gpu(raw_data: Dict[str, Any]) -> Optional[str]:
    """Extract dedicated GPU model from raw detection data"""
    # First, try to use the gpu_model that hardware_detector already parsed correctly
    if (
        "gpu_model" in raw_data
        and raw_data.get("gpu_type") == "Dedicated or Discrete GPU"
    ):
        return raw_data["gpu_model"]

    # Fallback: Check if GPUs list exists and parse manually
    if "gpus" in raw_data and raw_data["gpus"]:
        for gpu_line in raw_data["gpus"]:
            # Look for NVIDIA dedicated graphics
            if "nvidia" in gpu_line.lower():
                # Extract GPU name from brackets if present
                bracket_match = re.search(r'\[(.+?)\]', gpu_line)
                if bracket_match:
                    return f"NVIDIA {bracket_match.group(1)}"
                parts = gpu_line.split("controller:")
                if len(parts) > 1:
                    return parts[1].strip().split("(")[0].strip()
            # Look for AMD dedicated graphics (discrete Radeon)
            if (
                "amd" in gpu_line.lower()
                and "radeon" in gpu_line.lower()
                and "rx" in gpu_line.lower()
            ):
                # Extract GPU name from brackets if present
                bracket_match = re.search(r'\[(.+?)\]', gpu_line)
                if bracket_match:
                    return f"AMD {bracket_match.group(1)}"
                parts = gpu_line.split("controller:")
                if len(parts) > 1:
                    return parts[1].strip().split("(")[0].strip()

    return None


def has_dedicated_gpu(raw_data: Dict[str, Any]) -> bool:
    """Check if laptop has dedicated GPU"""
    dedicated = extract_dedicated_gpu(raw_data)
    return dedicated is not None


def upload_to_database(
    supabase: Client, raw_data: Dict[str, Any], bestbuy_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Upload hardware detection data to Supabase database

    Returns:
        Dict with model_id, variant_id, shop_sku, and status
    """

    print("\n" + "=" * 60)
    print("📤 Uploading to Supabase Database")
    print("=" * 60 + "\n")

    # Extract GPU information
    integrated_gpu = extract_integrated_gpu(raw_data)
    dedicated_gpu = extract_dedicated_gpu(raw_data)
    has_dedicated = has_dedicated_gpu(raw_data)

    # Step 1: Create or find laptop_models entry
    print("🔍 Checking for existing model...")

    # Determine touchscreen status
    has_touchscreen = bestbuy_data.get("_TouchscreenDisplay_23335_CAT_1002_EN") == "Yes"

    model_data = {
        "base_model_name": raw_data.get("model", "Unknown Model"),
        "cpu_model": raw_data.get("cpu_model", "Unknown CPU"),
        "screen_size_inches": raw_data.get("screen_size_inches"),
        "has_touchscreen": has_touchscreen,
        "integrated_gpu_model": integrated_gpu,
        "dedicated_gpu_model": dedicated_gpu,
    }

    # Check if model exists (exact match on unique constraint fields)
    try:
        # Use explicit field matching to ensure exact comparison
        query = (
            supabase.table("laptop_models")
            .select("id")
            .eq("base_model_name", model_data["base_model_name"])
            .eq("cpu_model", model_data["cpu_model"])
            .eq("screen_size_inches", model_data["screen_size_inches"])
            .eq("has_touchscreen", model_data["has_touchscreen"])
        )

        # Handle nullable GPU fields
        if model_data["integrated_gpu_model"] is None:
            query = query.is_("integrated_gpu_model", None)
        else:
            query = query.eq("integrated_gpu_model", model_data["integrated_gpu_model"])

        if model_data["dedicated_gpu_model"] is None:
            query = query.is_("dedicated_gpu_model", None)
        else:
            query = query.eq("dedicated_gpu_model", model_data["dedicated_gpu_model"])

        existing_model = query.execute()

        if existing_model.data and len(existing_model.data) > 0:
            model_id = existing_model.data[0]["id"]
            print(f"✅ Found existing model: {model_id}")
            print(f"   ℹ️  Skipping model creation (exact match found)")

            # Return early - skip if exists
            return {
                "model_id": model_id,
                "variant_id": None,
                "shop_sku": None,
                "status": "exists",
                "message": "Model already exists in database. No changes made.",
            }
        else:
            # Insert new model
            print("✨ Creating new model...")
            new_model = supabase.table("laptop_models").insert(model_data).execute()
            model_id = new_model.data[0]["id"]
            print(f"✅ Created new model: {model_id}")
    except Exception as e:
        print(f"❌ Error checking/creating model: {e}")
        raise

    # Step 2: Insert laptop_hardware_data
    print("\n📊 Inserting hardware data...")

    hardware_data = {
        "model_id": model_id,
        "brand": raw_data.get("brand"),
        "model": raw_data.get("model"),
        "manufacturer_sku": raw_data.get("sku"),
        "cpu_speed_ghz": raw_data.get("cpu_max_ghz") or raw_data.get("cpu_speed_ghz"),
        "cpu_cores": raw_data.get("cpu_cores"),
        "cpu_cache": raw_data.get("cpu_l3_cache"),
        "ram_type": raw_data.get("ram_type"),
        "screen_resolution": raw_data.get("screen_resolution"),
        "has_touchscreen": has_touchscreen,
        "integrated_gpu_model": integrated_gpu,
        "dedicated_gpu_model": dedicated_gpu,
        "has_dedicated_gpu": has_dedicated,
        "has_wifi": raw_data.get("has_wifi", False),
        "has_bluetooth": raw_data.get("has_bluetooth", False),
        "has_ethernet": raw_data.get("has_ethernet", False),
        "has_webcam": raw_data.get("has_webcam", False),
        "raw_detection_json": raw_data,
    }

    try:
        supabase.table("laptop_hardware_data").upsert(
            hardware_data, on_conflict="model_id"
        ).execute()
        print("✅ Hardware data saved")
    except Exception as e:
        print(f"❌ Error inserting hardware data: {e}")
        raise

    # Step 3: Create default variant based on detected RAM/SSD
    print("\n💾 Creating default variant...")

    ram_gb = int(raw_data.get("ram_size_gb", 0))
    ssd_gb = raw_data.get("ssd_capacity_gb", 0)

    variant_data = {
        "model_id": model_id,
        "ram_size_gb": ram_gb,
        "ssd_capacity_gb": ssd_gb,
        "price": None,  # User fills later
    }

    try:
        # Check if variant exists
        existing_variant = (
            supabase.table("laptop_variants")
            .select("id, shop_sku")
            .match(
                {"model_id": model_id, "ram_size_gb": ram_gb, "ssd_capacity_gb": ssd_gb}
            )
            .execute()
        )

        if existing_variant.data and len(existing_variant.data) > 0:
            variant_id = existing_variant.data[0]["id"]
            shop_sku = existing_variant.data[0]["shop_sku"]
            print(f"ℹ️  Found existing variant: {variant_id}")
            print(f"   SKU: {shop_sku}")
            print(f"   {ram_gb}GB RAM / {ssd_gb}GB SSD")
        else:
            # Insert new variant
            new_variant = (
                supabase.table("laptop_variants").insert(variant_data).execute()
            )
            variant_id = new_variant.data[0]["id"]
            shop_sku = new_variant.data[0]["shop_sku"]
            print(f"✅ Created new variant: {variant_id}")
            print(f"   SKU: {shop_sku}")
            print(f"   {ram_gb}GB RAM / {ssd_gb}GB SSD")
    except Exception as e:
        print(f"❌ Error creating variant: {e}")
        raise

    # Step 4: Create inventory record
    print("\n📦 Initializing inventory tracking...")

    inventory_data = {"model_id": model_id, "inventory_count": 0, "damaged_count": 0}

    try:
        supabase.table("laptops").upsert(
            inventory_data, on_conflict="model_id"
        ).execute()
        print("✅ Inventory record created (count = 0)")
    except Exception as e:
        print(f"❌ Error creating inventory record: {e}")
        raise

    # Step 5: Save manual fields to laptop_manual_fields
    print("\n📝 Saving manual fields...")

    # Extract manual fields from bestbuy_data and map to database columns
    manual_fields_data = {
        "variant_id": variant_id,
        "keyboard_language": bestbuy_data.get("_KeyboardLanguage_24678_CAT_1002_EN"),
        "backlit_keyboard": bestbuy_data.get("_BacklitKeyboard_24680_CAT_1002_EN") == "Yes",
        "convertible_hybrid": bestbuy_data.get("_ConvertibleHybridDisplay_36185_CAT_1002_EN") == "Yes",
        "colour": bestbuy_data.get("_Colour_5105_CAT_1002_EN"),
        "product_condition": bestbuy_data.get("_ProductCondition_20257570_CAT_1002_EN"),
    }

    # Remove None values to avoid inserting nulls for fields that weren't provided
    manual_fields_data = {k: v for k, v in manual_fields_data.items() if v is not None}

    try:
        if len(manual_fields_data) > 1:  # More than just variant_id
            supabase.table("laptop_manual_fields").upsert(
                manual_fields_data, on_conflict="variant_id"
            ).execute()
            print("✅ Manual fields saved")
            print(f"   - Color: {manual_fields_data.get('colour', 'N/A')}")
            print(f"   - Keyboard: {manual_fields_data.get('keyboard_language', 'N/A')}")
            print(f"   - Backlit: {manual_fields_data.get('backlit_keyboard', 'N/A')}")
            print(f"   - Condition: {manual_fields_data.get('product_condition', 'N/A')}")
        else:
            print("ℹ️  No manual fields to save")
    except Exception as e:
        print(f"❌ Error saving manual fields: {e}")
        raise

    print("\n" + "=" * 60)
    print("✅ Upload Complete!")
    print("=" * 60 + "\n")

    return {
        "model_id": model_id,
        "variant_id": variant_id,
        "shop_sku": shop_sku,
        "status": "created",
        "message": "Successfully created model, hardware data, variant, inventory, and manual fields.",
    }
