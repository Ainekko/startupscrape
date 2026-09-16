import json
import html
from startupscrape.enrichers import YCEnricher
from startupscrape.models import StartupLead, Founder


def test_normalize_company_url():
    enricher = YCEnricher()
    assert enricher.normalize_company_url("oklo") == "https://www.ycombinator.com/companies/oklo"
    assert enricher.normalize_company_url("https://www.ycombinator.com/companies/stripe/") == "https://www.ycombinator.com/companies/stripe"
    assert enricher.normalize_company_url("https://www.ycombinator.com/companies/airbnb?batch=W09") == "https://www.ycombinator.com/companies/airbnb"


def test_extract_slug():
    enricher = YCEnricher()
    assert enricher.extract_slug("oklo") == "oklo"
    assert enricher.extract_slug("https://www.ycombinator.com/companies/resend") == "resend"
    assert enricher.extract_slug("https://www.ycombinator.com/companies/resend/?query=1") == "resend"


def test_parse_html_with_inertia_data():
    enricher = YCEnricher()
    company_data = {
        "props": {
            "company": {
                "name": "SuperTech",
                "website": "https://supertech.io",
                "linkedin_url": "https://www.linkedin.com/company/supertech-io",
                "twitter_url": "https://twitter.com/supertech_io",
                "founders": [
                    {
                        "full_name": "Jane Doe",
                        "title": "Founder/CEO",
                        "linkedin_url": "https://linkedin.com/in/janedoe",
                        "twitter_url": "https://twitter.com/janedoe",
                        "founder_bio": "Ex-Stripe engineer, building AI workflows",
                        "has_email": True
                    }
                ]
            }
        }
    }
    raw_json = json.dumps(company_data)
    escaped_json = html.escape(raw_json)
    html_content = f'<html><body><div id="app" data-page="{escaped_json}"></div></body></html>'

    result = enricher.parse_html(html_content)
    assert result["website"] == "https://supertech.io"
    assert result["linkedin_url"] == "https://www.linkedin.com/company/supertech-io"
    assert result["twitter_url"] == "https://twitter.com/supertech_io"
    assert len(result["founders"]) == 1
    f = result["founders"][0]
    assert f.name == "Jane Doe"
    assert f.title == "Founder/CEO"
    assert f.linkedin_url == "https://linkedin.com/in/janedoe"
    assert f.bio == "Ex-Stripe engineer, building AI workflows"
    assert f.has_email is True


def test_parse_html_regex_fallback():
    enricher = YCEnricher()
    html_content = """
    <html>
        <body>
            <a href="https://example-saas.com" class="inline-block">Website</a>
            <a href="https://www.linkedin.com/company/example-saas/">LinkedIn</a>
            <a href="https://twitter.com/example_saas">Twitter</a>
            <a href="https://twitter.com/ycombinator">YC Twitter</a>
        </body>
    </html>
    """
    result = enricher.parse_html(html_content)
    assert result["website"] == "https://example-saas.com"
    assert result["linkedin_url"] == "https://www.linkedin.com/company/example-saas"
    assert result["twitter_url"] == "https://twitter.com/example_saas"


def test_enrich_lead_updates_fields(monkeypatch):
    enricher = YCEnricher()

    def mock_fetch(target):
        return {
            "website": "https://enriched.ai",
            "linkedin_url": "https://linkedin.com/company/enriched-ai",
            "twitter_url": "https://twitter.com/enriched_ai",
            "founders": [
                Founder(name="John Doe", title="CEO", linkedin_url="https://linkedin.com/in/johndoe", has_email=True)
            ],
            "jobs": []
        }

    monkeypatch.setattr(enricher, "fetch_company_enrichment", mock_fetch)

    lead = StartupLead(id="enriched", source="yc", name="Enriched AI", slug="enriched")
    updated = enricher.enrich_lead(lead)

    assert updated.website == "https://enriched.ai"
    assert updated.linkedin_url == "https://linkedin.com/company/enriched-ai"
    assert updated.twitter_url == "https://twitter.com/enriched_ai"
    assert len(updated.founders) == 1
    assert updated.founders[0].name == "John Doe"
    assert updated.founders[0].has_email is True
