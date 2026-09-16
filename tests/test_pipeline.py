import pytest
from startupscrape.models import StartupLead, JobPosting
from startupscrape.pipeline import StartupScrapePipeline


@pytest.fixture
def pipeline():
    return StartupScrapePipeline()


def test_normalize_domain(pipeline):
    assert pipeline._normalize_domain("https://www.example.com") == "example.com"
    assert pipeline._normalize_domain("http://example.com/test?a=1") == "example.com"
    assert pipeline._normalize_domain("subdomain.domain.co.uk/") == "subdomain.domain.co.uk"
    assert pipeline._normalize_domain("https://WWW.UPPERCASE.COM") == "uppercase.com"
    assert pipeline._normalize_domain("") is None
    assert pipeline._normalize_domain(None) is None


def test_normalize_name(pipeline):
    assert pipeline._normalize_name("Acme, Inc.") == "acme inc"
    assert pipeline._normalize_name("  Stripe - Payments!  ") == "stripe payments"
    assert pipeline._normalize_name("Scale.ai") == "scaleai"


def test_deduplicate_and_merge_by_domain(pipeline):
    lead_yc = StartupLead(
        id="acme-yc",
        source="yc",
        name="Acme Inc",
        website="https://acme.com",
        batch="W24",
        yc_url="https://ycombinator.com/companies/acme"
    )
    lead_waas = StartupLead(
        id="acme-waas",
        source="workatastartup",
        name="Acme",
        website="https://www.acme.com/",
        linkedin_url="https://linkedin.com/company/acme",
        waas_url="https://workatastartup.com/companies/acme",
        jobs=[
            JobPosting(id="1", title="Founding AE")
        ]
    )

    merged = pipeline.deduplicate_and_merge([lead_yc, lead_waas])
    assert len(merged) == 1
    lead = merged[0]
    assert lead.name == "Acme Inc"
    assert lead.batch == "W24"
    assert lead.yc_url == "https://ycombinator.com/companies/acme"
    assert lead.waas_url == "https://workatastartup.com/companies/acme"
    assert lead.linkedin_url == "https://linkedin.com/company/acme"
    assert len(lead.jobs) == 1
    assert lead.is_hiring is True
    assert lead.open_jobs_count == 1


def test_deduplicate_and_merge_by_name(pipeline):
    lead_yc = StartupLead(
        id="beta-yc",
        source="yc",
        name="Beta Labs",
        website=None,
        one_liner="AI tools for builders"
    )
    lead_waas = StartupLead(
        id="beta-waas",
        source="workatastartup",
        name="Beta Labs!",
        website="https://betalabs.io",
        team_size=15
    )

    merged = pipeline.deduplicate_and_merge([lead_yc, lead_waas])
    assert len(merged) == 1
    lead = merged[0]
    assert lead.name == "Beta Labs"
    assert lead.website == "https://betalabs.io"
    assert lead.team_size == 15
    assert lead.one_liner == "AI tools for builders"


def test_deduplicate_distinct_leads(pipeline):
    lead1 = StartupLead(id="1", source="yc", name="Company One", website="https://one.com")
    lead2 = StartupLead(id="2", source="yc", name="Company Two", website="https://two.com")
    merged = pipeline.deduplicate_and_merge([lead1, lead2])
    assert len(merged) == 2
