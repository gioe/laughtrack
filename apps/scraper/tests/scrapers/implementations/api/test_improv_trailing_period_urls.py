from laughtrack.scrapers.implementations.venues.improv.extractor import ImprovExtractor


def test_improv_trailing_period_comic_profile_links_are_not_ticket_links():
    html = """
    <a class="item" href="/denver/event/chris+porter/">Chris Porter</a>
    <a class="item" href="/denver/comic/chris+porter/">Chris Porter bio</a>
    <a class="item" href="/denver/comic/jack+assadourian+jr./">Jack Assadourian Jr.</a>
    <a class="item" href="/denver/comic/jane+comic+sr./">Jane Comic Sr.</a>
    """

    links = ImprovExtractor.extract_ticket_links(html, "https://improv.com")

    assert links == [
        "https://improv.com/denver/event/chris+porter/",
        "https://improv.com/denver/comic/chris+porter/",
    ]
