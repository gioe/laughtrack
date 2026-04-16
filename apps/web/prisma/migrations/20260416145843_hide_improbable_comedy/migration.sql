-- Improbable Comedy (club 809) is a production company, not a physical venue.
-- Hide the club record and create a ProductionCompany record instead.

-- Hide the club entry (not a venue)
UPDATE clubs SET visible = false WHERE id = 809;

-- Create as a production company
INSERT INTO production_companies (name, slug, website, scraping_url, visible, show_name_keywords)
VALUES (
    'Improbable Comedy',
    'improbable-comedy',
    'https://www.improbablecomedy.com',
    'https://www.eventbrite.com/o/improbable-comedy-10899180919',
    true,
    ARRAY['comedy', 'stand-up', 'standup', 'stand up', 'improv', 'open mic', 'open-mic', 'comedian', 'comic', 'laugh', 'humor', 'jokes', 'storytelling']
)
ON CONFLICT (name) DO NOTHING;
