import csv
import json
import os
from datetime import datetime
from typing import List
from .config import DATA_DIR
from .models import StartupLead


def export_to_csv(leads: List[StartupLead], filepath: str) -> str:
    """Export list of StartupLead to a CSV file."""
    if not leads:
        return filepath

    fieldnames = list(leads[0].to_flat_dict().keys())
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_flat_dict())

    return filepath


def export_to_json(leads: List[StartupLead], filepath: str) -> str:
    """Export list of StartupLead to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    data = [lead.model_dump(exclude={"raw_data"}) for lead in leads]
    with open(filepath, mode="w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def export_leads(leads: List[StartupLead], prefix: str = "startup_leads") -> dict:
    """Export leads to both CSV and JSON in the data directory with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(DATA_DIR, f"{prefix}_{timestamp}.csv")
    json_path = os.path.join(DATA_DIR, f"{prefix}_{timestamp}.json")

    export_to_csv(leads, csv_path)
    export_to_json(leads, json_path)

    return {
        "count": len(leads),
        "csv": csv_path,
        "json": json_path
    }
