"""Safely synchronize model-coverage entries from the serialized label encoder.

This script never creates agronomic constraints. Existing sourced knowledge
profiles are preserved. Use --check in CI/startup validation workflows; writing
requires an explicit --write flag.
"""

import argparse
import json
import sys
from pathlib import Path

import joblib


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = BACKEND_ROOT / "artifacts" / "xgboost_crop_model.joblib"
DEFAULT_CATALOG = BACKEND_ROOT / "app" / "data" / "crop_catalog.v1.json"


def canonical(value: str) -> str:
    return "".join(character for character in value.strip().lower() if character.isalnum())


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize crop catalogue model coverage")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--write", action="store_true", help="Write missing model entries and coverage flags")
    args = parser.parse_args()

    artifact = joblib.load(args.model)
    classes = [canonical(str(item)) for item in artifact["label_encoder"].classes_.tolist()]
    payload = json.loads(args.catalog.read_text(encoding="utf-8"))
    profiles = {canonical(item["crop_slug"]): item for item in payload.get("profiles", [])}
    catalog_model = {
        slug
        for slug, item in profiles.items()
        if item.get("is_model_supported", payload.get("profile_defaults", {}).get("is_model_supported", False))
    }
    missing = sorted(set(classes) - set(profiles))
    stale = sorted(catalog_model - set(classes))
    if not args.write:
        if missing or stale:
            print(f"Missing model classes: {missing}")
            print(f"Stale model flags: {stale}")
            return 1
        print(f"Catalogue matches {len(classes)} serialized model classes")
        return 0

    for slug in missing:
        profiles[slug] = {
            "crop_slug": slug,
            "display_name": slug.replace("beans", " beans").replace("peas", " peas").title(),
            "is_model_supported": True,
            "knowledge_profile_complete": False,
        }
    for slug, item in profiles.items():
        item["is_model_supported"] = slug in classes
    payload["profiles"] = sorted(profiles.values(), key=lambda item: item["crop_slug"])
    args.catalog.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Synchronized {len(classes)} model classes; no agronomic constraints were generated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
