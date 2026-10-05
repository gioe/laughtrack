-- TASK-4103: fixed audited cohort only; other promotion rows are not cleanup targets.
-- The source title rule prevents new ingestion once the matching scraper ships.
-- Click attribution survives via the existing ON DELETE SET NULL foreign key.
DO $cleanup$
DECLARE
    deleted_count integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM scraping_sources WHERE id=5914 AND club_id=8856
        AND source_url='https://tockify.com/api/ngevent?calname=queseralb&max=200') THEN
        RAISE EXCEPTION 'TASK-4103: Que Sera source identity changed';
    END IF;
    PERFORM 1 FROM scraping_sources WHERE id=5914 FOR UPDATE;
    IF EXISTS (SELECT 1 FROM scraping_sources WHERE id=5914
        AND metadata ? 'exclude_title_patterns'
        AND jsonb_typeof(metadata->'exclude_title_patterns') <> 'array') THEN
        RAISE EXCEPTION 'TASK-4103: unexpected existing title exclusion metadata';
    END IF;
    UPDATE scraping_sources SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb),
        '{exclude_title_patterns}',
        COALESCE(metadata->'exclude_title_patterns', '[]'::jsonb) || '["^After Comedy Happy Hour$"]'::jsonb)
    WHERE id=5914 AND NOT COALESCE(metadata->'exclude_title_patterns', '[]'::jsonb)
        @> '["^After Comedy Happy Hour$"]'::jsonb;

    CREATE TEMP TABLE task4103_cohort (show_id integer PRIMARY KEY, ticket_id integer,
        date timestamptz, url text) ON COMMIT DROP;
    INSERT INTO task4103_cohort VALUES
(2995475, 3256476, '2026-10-01T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1790829000000'),
(2995479, 3256480, '2026-10-08T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1791433800000'),
(2995483, 3256484, '2026-10-15T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1792038600000'),
(2995489, 3256490, '2026-10-22T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1792643400000'),
(2995493, 3256494, '2026-10-29T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1793248200000'),
(2995497, 3256498, '2026-11-05T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1793856600000'),
(2995501, 3256502, '2026-11-12T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1794461400000'),
(2995506, 3256507, '2026-11-19T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1795066200000'),
(2995511, 3256512, '2026-11-26T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1795671000000'),
(2995515, 3256516, '2026-12-03T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1796275800000'),
(2995519, 3256520, '2026-12-10T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1796880600000'),
(2995523, 3256524, '2026-12-17T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1797485400000'),
(2995529, 3256530, '2026-12-24T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1798090200000'),
(2995533, 3256534, '2026-12-31T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1798695000000'),
(2995537, 3256538, '2027-01-07T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1799299800000'),
(2995541, 3256542, '2027-01-14T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1799904600000'),
(2995547, 3256548, '2027-01-21T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1800509400000'),
(2995551, 3256552, '2027-01-28T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1801114200000'),
(2995555, 3256556, '2027-02-04T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1801719000000'),
(2995559, 3256560, '2027-02-11T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1802323800000'),
(2995563, 3256564, '2027-02-18T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1802928600000'),
(2995569, 3256570, '2027-02-25T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1803533400000'),
(2995573, 3256574, '2027-03-04T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1804138200000'),
(2995577, 3256578, '2027-03-11T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1804743000000'),
(2995581, 3256582, '2027-03-18T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1805344200000'),
(2995587, 3256588, '2027-03-25T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1805949000000'),
(2995591, 3256592, '2027-04-01T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1806553800000'),
(2995595, 3256596, '2027-04-08T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1807158600000'),
(2995599, 3256600, '2027-04-15T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1807763400000'),
(3385248, 3717151, '2027-04-22T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1808368200000'),
(3651382, 4088872, '2027-04-29T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1808973000000'),
(3976500, 4463863, '2027-05-06T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1809577800000'),
(2995617, 3256618, '2027-05-13T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1810182600000'),
(7074297, 8052353, '2027-05-20T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1810787400000'),
(7207897, 8208550, '2027-05-27T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1811392200000'),
(7340034, 8362311, '2027-06-03T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1811997000000'),
(5439144, 6155809, '2027-06-10T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1812601800000'),
(5757676, 6524714, '2027-06-17T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1813206600000'),
(6382578, 7249308, '2027-06-24T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1813811400000'),
(6547003, 7439193, '2027-07-01T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1814416200000'),
(6796979, 7729249, '2027-07-08T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1815021000000'),
(6949212, 7905843, '2027-07-15T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1815625800000'),
(2995663, 3256664, '2027-07-22T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1816230600000'),
(2995667, 3256668, '2027-07-29T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1816835400000'),
(2995671, 3256672, '2027-08-05T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1817440200000'),
(2995675, 3256676, '2027-08-12T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1818045000000'),
(2995680, 3256681, '2027-08-19T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1818649800000'),
(2995685, 3256686, '2027-08-26T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1819254600000'),
(2995689, 3256690, '2027-09-02T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1819859400000'),
(2995693, 3256694, '2027-09-09T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1820464200000'),
(2995697, 3256698, '2027-09-16T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1821069000000'),
(2995703, 3256704, '2027-09-23T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1821673800000'),
(2995707, 3256708, '2027-09-30T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1822278600000'),
(2995711, 3256712, '2027-10-07T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1822883400000'),
(2995715, 3256716, '2027-10-14T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1823488200000'),
(2995721, 3256722, '2027-10-21T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1824093000000'),
(2995725, 3256726, '2027-10-28T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1824697800000'),
(2995729, 3256730, '2027-11-04T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1825302600000'),
(2995733, 3256734, '2027-11-11T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1825911000000'),
(2995737, 3256738, '2027-11-18T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1826515800000'),
(2995743, 3256744, '2027-11-25T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1827120600000'),
(2995747, 3256748, '2027-12-02T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1827725400000'),
(2995751, 3256752, '2027-12-09T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1828330200000'),
(2995755, 3256756, '2027-12-16T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1828935000000'),
(3299698, 3616495, '2027-12-23T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1829539800000'),
(3555850, 3978519, '2027-12-30T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1830144600000'),
(3838644, 4305015, '2028-01-06T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1830749400000'),
(4150979, 4665263, '2028-01-13T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1831354200000'),
(4462607, 5024929, '2028-01-20T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1831959000000'),
(4678267, 5277068, '2028-01-27T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1832563800000'),
(4926897, 5567606, '2028-02-03T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1833168600000'),
(5278180, 5969615, '2028-02-10T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1833773400000'),
(5658375, 6410021, '2028-02-17T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1834378200000'),
(5958450, 6756912, '2028-02-24T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1834983000000'),
(6382650, 7249380, '2028-03-02T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1835587800000'),
(6750776, 7675164, '2028-03-09T05:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1836192600000'),
(7074383, 8052439, '2028-03-16T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1836793800000'),
(7410667, 8443389, '2028-03-23T04:30:00+00:00'::timestamptz, 'https://tockify.com/queseralb/detail/315/1837398600000');
    PERFORM 1 FROM shows s JOIN task4103_cohort c ON c.show_id=s.id FOR UPDATE OF s;
    IF EXISTS (SELECT 1 FROM shows s JOIN task4103_cohort c ON c.show_id=s.id
        WHERE s.club_id<>8856 OR s.name IS DISTINCT FROM 'After Comedy Happy Hour'
        OR s.date<>c.date OR s.show_page_url<>c.url OR s.last_scraped_by IS DISTINCT FROM 'tockify') THEN
        RAISE EXCEPTION 'TASK-4103: audited promotion identity drift';
    END IF;
    IF EXISTS (SELECT 1 FROM tickets t JOIN task4103_cohort c ON c.show_id=t.show_id
        WHERE t.id<>c.ticket_id OR t.price IS NOT NULL) THEN
        RAISE EXCEPTION 'TASK-4103: unexpected ticket or admission-price drift';
    END IF;
    IF EXISTS (SELECT 1 FROM lineup_items WHERE show_id IN (SELECT show_id FROM task4103_cohort))
        OR EXISTS (SELECT 1 FROM saved_shows WHERE show_id IN (SELECT show_id FROM task4103_cohort))
        OR EXISTS (SELECT 1 FROM sent_notifications WHERE show_id IN (SELECT show_id FROM task4103_cohort))
        OR EXISTS (SELECT 1 FROM discovery_show_feature_snapshots WHERE show_id IN (SELECT show_id FROM task4103_cohort)) THEN
        RAISE EXCEPTION 'TASK-4103: protected dependencies appeared; retain shows for review';
    END IF;
    PERFORM 1 FROM ticket_purchase_click_events WHERE show_id IN
        (SELECT show_id FROM task4103_cohort) FOR UPDATE;
    CREATE TEMP TABLE task4103_clicks ON COMMIT DROP AS
        SELECT id, to_jsonb(t)-'show_id' AS attribution FROM ticket_purchase_click_events t
        WHERE show_id IN (SELECT show_id FROM task4103_cohort);
    DELETE FROM shows WHERE id IN (SELECT show_id FROM task4103_cohort);
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    IF EXISTS (SELECT 1 FROM task4103_clicks c LEFT JOIN ticket_purchase_click_events t ON t.id=c.id
        WHERE t.id IS NULL OR t.show_id IS NOT NULL OR to_jsonb(t)-'show_id' IS DISTINCT FROM c.attribution) THEN
        RAISE EXCEPTION 'TASK-4103: click attribution was not preserved';
    END IF;
    UPDATE clubs SET total_shows=(SELECT count(*) FROM shows WHERE club_id=8856) WHERE id=8856;
    RAISE NOTICE 'TASK-4103: removed % audited promotions; preserved % click records',
        deleted_count, (SELECT count(*) FROM task4103_clicks);
END
$cleanup$;
