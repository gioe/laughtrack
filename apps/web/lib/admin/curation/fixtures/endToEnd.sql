-- Minimal pre-curation schema shared by PGlite and native PostgreSQL checks.
CREATE TABLE comedians(id serial PRIMARY KEY,uuid text UNIQUE,name text,visible boolean DEFAULT true,parent_comedian_id int,block_reason text,block_added_by text,block_added_at timestamptz,total_shows int DEFAULT 0,instagram_followers int,bandsintown_id text);
 CREATE TABLE clubs(id serial PRIMARY KEY,name text UNIQUE,address text,website text DEFAULT '',city text,state text,country text,google_place_id text,visible boolean DEFAULT true,status text DEFAULT 'active',club_type text DEFAULT 'club');
 CREATE TABLE shows(id serial PRIMARY KEY,name text,club_id int REFERENCES clubs ON DELETE CASCADE,date timestamptz NOT NULL, room text, show_page_url text, source_performance_id text, is_cancelled boolean DEFAULT false);
 CREATE TABLE podcasts(id serial PRIMARY KEY,source text,source_podcast_id text,title text,feed_url text,external_ids jsonb DEFAULT '{}',UNIQUE(source,source_podcast_id));
CREATE TABLE podcast_episodes(id serial PRIMARY KEY,podcast_id int REFERENCES podcasts,title text);
CREATE TABLE podcast_deny_list(id serial PRIMARY KEY,podcast_id int REFERENCES podcasts ON DELETE SET NULL,source text,source_podcast_id text,feed_url text,reason text,denied_by text,denied_at timestamptz DEFAULT now(),restored_at timestamptz,restored_by text);
CREATE TABLE comedian_podcasts(id serial PRIMARY KEY,comedian_id int,podcast_id int,association_type text,source text,review_status text DEFAULT 'pending',confidence float DEFAULT 1,evidence jsonb DEFAULT '{}',reviewed_at timestamptz,reviewed_by text,created_at timestamptz DEFAULT now(),updated_at timestamptz DEFAULT now(),UNIQUE(comedian_id,podcast_id,association_type,source));
CREATE TABLE podcast_candidate_reviews(id serial PRIMARY KEY,comedian_id int,podcast_id int,association_type text,source text,source_podcast_id text,candidate_status text DEFAULT 'pending',confidence float DEFAULT 1,evidence jsonb DEFAULT '{}',reviewed_at timestamptz,reviewed_by text,created_at timestamptz DEFAULT now(),updated_at timestamptz DEFAULT now());
 CREATE TABLE lineup_items(show_id int,comedian_id text);
 CREATE TABLE comedian_deny_list(name text PRIMARY KEY);
 CREATE TABLE venue_deny_list(google_place_id text PRIMARY KEY,name text,reason text,added_by text);
 CREATE TABLE club_aliases(id serial PRIMARY KEY,club_id int REFERENCES clubs ON DELETE CASCADE,alias_name text,city text,state text,verified boolean DEFAULT true);
 CREATE TABLE scraping_sources(id serial PRIMARY KEY,club_id int REFERENCES clubs ON DELETE CASCADE,platform text,seatengine_id int,seatengine_v3_id text,ticketmaster_id text,eventbrite_id text,enabled boolean DEFAULT true,comedy_gate_mode text DEFAULT 'enforce',metadata jsonb DEFAULT '{}');
