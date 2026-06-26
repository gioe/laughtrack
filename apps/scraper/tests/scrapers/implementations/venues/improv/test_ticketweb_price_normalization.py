from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.venues.improv.extractor import ImprovExtractor


def _club() -> Club:
    return Club(
        id=1,
        name="Test Improv",
        address="123 Main St",
        website="https://improv.test",
        popularity=0,
        zip_code="00000",
        phone_number="000-0000",
        visible=True,
        timezone="America/New_York",
    )


def _ticketweb_html(body: str, price: str = "0") -> str:
    return f"""
    <html>
      <head>
        <script type="application/ld+json">
        {{
          "@context": "https://schema.org",
          "@type": "Event",
          "name": "Sample Comic",
          "startDate": "2026-07-15T19:30:00-05:00",
          "url": "https://www.ticketweb.com/event/sample-comic-test-improv-tickets/12345",
          "description": "Comedy show",
          "location": {{
            "@type": "Place",
            "name": "Test Improv",
            "address": {{
              "@type": "PostalAddress",
              "streetAddress": "123 Main St",
              "addressLocality": "Austin",
              "addressRegion": "TX",
              "postalCode": "78701",
              "addressCountry": "US"
            }}
          }},
          "offers": {{
            "@type": "Offer",
            "url": "https://www.ticketweb.com/event/sample-comic-test-improv-tickets/12345",
            "price": "{price}",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "name": "General Admission"
          }}
        }}
        </script>
      </head>
      <body>{body}</body>
    </html>
    """


def _show_from_ticketweb_html(html: str):
    events = ImprovExtractor.process_ticket_url(
        html,
        "https://www.ticketweb.com/event/sample-comic-test-improv-tickets/12345",
    )
    assert events
    return events[0].to_show(_club())


def test_ticketweb_zero_price_without_explicit_free_text_becomes_unknown():
    show = _show_from_ticketweb_html(_ticketweb_html("<p>Buy Tickets</p>"))

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price is None
    assert show.tickets[0].sold_out is False


def test_ticketweb_explicit_free_ticket_selector_keeps_zero_price():
    show = _show_from_ticketweb_html(_ticketweb_html("""
            <section>
              <h2>Select Tickets</h2>
              <div>General Admission $0.00 ($0.00 + $0.00 fees)</div>
            </section>
            """))

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 0.0
    assert show.tickets[0].sold_out is False


def test_ticketweb_unavailable_page_marks_ticket_sold_out_with_unknown_price():
    show = _show_from_ticketweb_html(_ticketweb_html("""
            <p>No more tickets currently available for purchase.</p>
            <p>JOIN OUR EMAIL WAITLIST</p>
            """))

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price is None
    assert show.tickets[0].sold_out is True


def test_ticketweb_positive_price_is_unchanged():
    show = _show_from_ticketweb_html(_ticketweb_html("<p>Select Tickets</p>", price="37.17"))

    assert show is not None
    assert len(show.tickets) == 1
    assert show.tickets[0].price == 37.17
    assert show.tickets[0].sold_out is False
