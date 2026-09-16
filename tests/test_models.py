import pytest
from startupscrape.models import Founder, JobPosting, GTMAnalysis, StartupLead, FilterQuery


def test_founder_model():
    founder = Founder(
        name="Alice Smith",
        title="CEO & Co-founder",
        twitter_url="https://twitter.com/alicesmith",
        linkedin_url="https://linkedin.com/in/alicesmith",
        bio="Ex-Google AI researcher, 2nd time founder",
        has_email=True
    )
    assert founder.name == "Alice Smith"
    assert founder.title == "CEO & Co-founder"
    assert founder.twitter_url == "https://twitter.com/alicesmith"
    assert founder.bio == "Ex-Google AI researcher, 2nd time founder"
    assert founder.has_email is True


def test_job_posting_model():
    job = JobPosting(
        id="job_123",
        title="Founding Account Executive",
        role_type="Sales",
        location="San Francisco, CA",
        has_salary=True,
        has_equity=True,
        visa_sponsored=False,
        url="https://workatastartup.com/jobs/123"
    )
    assert job.id == "job_123"
    assert job.title == "Founding Account Executive"
    assert job.has_salary is True
    assert job.visa_sponsored is False


def test_gtm_analysis_model_defaults():
    gtm = GTMAnalysis()
    assert gtm.score == 5
    assert gtm.stage == "Early"
    assert gtm.key_signals == []
    assert gtm.best_contact_role == "Founder / CEO"
    assert gtm.best_contact_name is None
    assert gtm.suggested_angle is None
    assert gtm.first_message is None


def test_startup_lead_defaults():
    lead = StartupLead(
        id="acme",
        source="yc",
        name="Acme Corp"
    )
    assert lead.id == "acme"
    assert lead.source == "yc"
    assert lead.name == "Acme Corp"
    assert lead.status == "Active"
    assert lead.is_hiring is False
    assert lead.open_jobs_count == 0
    assert lead.jobs == []
    assert lead.founders == []
    assert lead.tags == []
    assert lead.locations == []


def test_startup_lead_to_flat_dict():
    founder = Founder(
        name="Bob Builder",
        title="Founder / CEO",
        linkedin_url="https://linkedin.com/in/bobbuilder",
        bio="Civil engineer turned software builder",
        has_email=True
    )
    gtm = GTMAnalysis(
        score=9,
        stage="Seed",
        key_signals=["Hiring Founding AE", "Recent W25 Batch"],
        best_contact_role="Founder / CEO",
        best_contact_name="Bob Builder",
        best_contact_linkedin="https://linkedin.com/in/bobbuilder",
        suggested_angle="Building outbound pipeline with FlowJoy",
        first_message="Hi Bob, noticed your recent hiring for sales."
    )
    lead = StartupLead(
        id="acme_ai",
        source="yc",
        name="Acme AI",
        website="https://acme.ai",
        linkedin_url="https://linkedin.com/company/acme-ai",
        batch="W25",
        industry="B2B",
        team_size=12,
        is_hiring=True,
        open_jobs_count=3,
        founders=[founder],
        yc_url="https://www.ycombinator.com/companies/acme-ai",
        gtm_analysis=gtm
    )

    flat = lead.to_flat_dict()
    assert flat["ID"] == "acme_ai"
    assert flat["Source"] == "yc"
    assert flat["Company Name"] == "Acme AI"
    assert flat["Score"] == 9
    assert flat["Stage"] == "Seed"
    assert flat["Key Signals"] == "Hiring Founding AE; Recent W25 Batch"
    assert flat["Founder Name"] == "Bob Builder"
    assert flat["Founder LinkedIn"] == "https://linkedin.com/in/bobbuilder"
    assert flat["Founder Has Email"] == "Yes"
    assert flat["Founder Bio"] == "Civil engineer turned software builder"
    assert flat["Website"] == "https://acme.ai"
    assert flat["Is Hiring"] == "Yes"
    assert flat["Open Jobs Count"] == 3
    assert flat["YC URL"] == "https://www.ycombinator.com/companies/acme-ai"


def test_filter_query_defaults():
    query = FilterQuery()
    assert query.query_text == ""
    assert query.batches == []
    assert query.industries == []
    assert query.sort_by == "created_desc"
    assert query.limit == 50
    assert query.is_hiring is None
