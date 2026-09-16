import os
import json
import csv
from startupscrape.models import StartupLead, GTMAnalysis
from startupscrape.exporters import export_to_csv, export_to_json, export_leads


def test_export_to_csv(tmp_path):
    csv_file = str(tmp_path / "leads.csv")
    lead = StartupLead(
        id="test-1",
        source="yc",
        name="Export Test",
        website="https://export.test",
        gtm_analysis=GTMAnalysis(score=8, stage="Seed", key_signals=["Hiring Sales"])
    )
    result_path = export_to_csv([lead], csv_file)
    assert os.path.exists(result_path)

    with open(result_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["Company Name"] == "Export Test"
        assert rows[0]["Score"] == "8"
        assert rows[0]["Stage"] == "Seed"
        assert rows[0]["Key Signals"] == "Hiring Sales"


def test_export_to_json(tmp_path):
    json_file = str(tmp_path / "leads.json")
    lead = StartupLead(
        id="test-2",
        source="workatastartup",
        name="JSON Test",
        website="https://jsontest.com",
        raw_data={"internal_secret": 12345}
    )
    result_path = export_to_json([lead], json_file)
    assert os.path.exists(result_path)

    with open(result_path, mode="r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["name"] == "JSON Test"
        assert "raw_data" not in data[0]


def test_export_empty_leads(tmp_path):
    csv_file = str(tmp_path / "empty.csv")
    res = export_to_csv([], csv_file)
    assert res == csv_file
    assert not os.path.exists(csv_file)
