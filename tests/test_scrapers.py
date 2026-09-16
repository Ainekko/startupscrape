import json
import urllib.parse
from startupscrape.scrapers.yc import YCScraper
from startupscrape.scrapers.waas import WAASScraper
from startupscrape.models import FilterQuery


def test_yc_parse_directory_url():
    scraper = YCScraper()
    url = "https://www.ycombinator.com/companies/?batch=W24&industry=B2B&isHiring=true&team_size=%5B5%2C50%5D&q=fintech"
    query = scraper.parse_url(url)

    assert query.batches == ["W24"]
    assert query.industries == ["B2B"]
    assert query.is_hiring is True
    assert query.team_size_min == 5
    assert query.team_size_max == 50
    assert query.query_text == "fintech"


def test_yc_is_company_detail_url():
    scraper = YCScraper()
    assert scraper.is_company_detail_url("https://www.ycombinator.com/companies/stripe") is True
    assert scraper.is_company_detail_url("https://www.ycombinator.com/companies/airbnb/") is True
    assert scraper.is_company_detail_url("https://www.ycombinator.com/companies") is False
    assert scraper.is_company_detail_url("https://www.ycombinator.com/companies/?batch=W24") is False


def test_yc_build_algolia_params():
    scraper = YCScraper()
    filters = FilterQuery(
        batches=["W24", "S24"],
        industries=["B2B"],
        is_hiring=True,
        team_size_min=10,
        team_size_max=100
    )
    params_str = scraper._build_algolia_params(filters, page=1, hits_per_page=20)
    params = urllib.parse.parse_qs(params_str)

    assert params["page"] == ["1"]
    assert params["hitsPerPage"] == ["20"]

    # Verify facet filters
    facet_filters = json.loads(params["facetFilters"][0])
    flat_facets = [f for sub in facet_filters for f in sub]
    assert "batch:W24" in flat_facets
    assert "batch:S24" in flat_facets
    assert "industry:B2B" in flat_facets
    assert "isHiring:true" in flat_facets

    # Verify numeric filters
    numeric_filters = json.loads(params["numericFilters"][0])
    assert "team_size>=10" in numeric_filters
    assert "team_size<=100" in numeric_filters


def test_yc_parse_hit():
    scraper = YCScraper()
    mock_hit = {
        "objectID": "12345",
        "slug": "sample-ai",
        "name": "Sample AI",
        "website": "https://sample.ai",
        "one_liner": "Next-gen AI agents",
        "batch_name": "Winter 2025",
        "team_size": 8,
        "isHiring": True,
        "job_count": 2,
        "all_locations": "San Francisco, CA; Remote",
        "industry": "B2B",
        "subindustry": "AI"
    }

    lead = scraper._parse_hit(mock_hit)
    assert lead.id == "12345"
    assert lead.source == "yc"
    assert lead.name == "Sample AI"
    assert lead.slug == "sample-ai"
    assert lead.website == "https://sample.ai"
    assert lead.batch == "Winter 2025"
    assert lead.team_size == 8
    assert lead.is_hiring is True
    assert lead.open_jobs_count == 2
    assert "San Francisco, CA" in lead.locations
    assert "Remote" in lead.locations
    assert lead.yc_url == "https://www.ycombinator.com/companies/sample-ai"


def test_waas_parse_url():
    scraper = WAASScraper()
    url = "https://www.workatastartup.com/companies?locations=US&industry=B2B&jobType=Sales&hasSalary=true&hasEquity=true&usVisaNotRequired=true"
    query = scraper.parse_url(url)

    assert query.locations == ["US"]
    assert query.industries == ["B2B"]
    assert query.job_types == ["Sales"]
    assert query.has_salary is True
    assert query.has_equity is True
    assert query.visa_not_required is True


def test_waas_parse_hit():
    scraper = WAASScraper()
    mock_hit = {
        "objectID": "9876",
        "slug": "grow-fast",
        "name": "GrowFast",
        "website": "https://growfast.com",
        "description": "Outbound growth automation",
        "batch": "S24",
        "team_size": 20,
        "locations": ["New York, NY"],
        "jobs": [
            {
                "id": "job_1",
                "title": "Head of Sales",
                "role_type": "sales",
                "location": "New York, NY",
                "has_salary": True,
                "has_equity": True
            }
        ]
    }

    lead = scraper._parse_hit(mock_hit)
    assert lead.id == "9876"
    assert lead.source == "workatastartup"
    assert lead.name == "GrowFast"
    assert lead.is_hiring is True
    assert lead.open_jobs_count == 1
    assert len(lead.jobs) == 1
    assert lead.jobs[0].title == "Head of Sales"
    assert lead.jobs[0].has_salary is True
    assert lead.waas_url == "https://www.workatastartup.com/companies/grow-fast"
