"""Canonical-only frontend exporter with fixture isolation."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .pipeline import assert_formal_canonical
from .schema_validation import SchemaValidationError, load_schema, validate_instance


def _to_university_poi(record: Dict[str, Any]) -> Dict[str, Any]:
    university = record["university"]
    fields = record["frontend_fields"]
    return {
        "id": university["internal_id"],
        "name": university["official_name"],
        "chineseName": university["name_zh"],
        "country": "United States",
        "city": university["city"],
        "latitude": university["latitude"],
        "longitude": university["longitude"],
        "rankingBand": fields["rankingBand"],
        "rankingTier": fields["rankingTier"],
        "annualCostRmb": fields["annualCostRmb"],
        "safetyScore": fields["safetyScore"],
        "recognitionScore": fields["recognitionScore"],
        "chineseCommunity": fields["chineseCommunity"],
        "directFlight": fields["directFlight"],
        "postStudyVisa": fields["postStudyVisa"],
        "programs": fields["programs"],
        "parentHighlights": fields["parentHighlights"],
        "studentHighlights": fields["studentHighlights"],
        "verifiedAt": record["sources"][0]["accessed_at"],
        "sourceCount": len(record["sources"]),
        "campusImages": [],
        "nearby": fields["nearby"],
    }


def export_preview(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Render a test/dry-run preview from already canonical-compatible records."""
    pois = [_to_university_poi(record) for record in records]
    document = {
        "_instructions": "Generated preview only; never use as production data.",
        "_generatedBy": "pathos_data export preview",
        "universities": pois,
    }
    validate_instance(document, load_schema("frontend-universities.json"))
    return document


def write_formal_frontend_export(records: list[Dict[str, Any]], output_path: Path) -> None:
    """Write the formal JSON only from non-test, validated canonical records."""
    assert_formal_canonical(records)
    document = export_preview(records)
    if any(record["is_test_fixture"] for record in records):
        raise SchemaValidationError("Test fixture output is not a formal frontend export")
    output_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
