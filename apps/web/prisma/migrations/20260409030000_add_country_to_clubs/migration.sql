-- AlterTable: add nullable country column
ALTER TABLE "clubs" ADD COLUMN "country" TEXT;

-- Backfill: set country = 'US' for all clubs with a valid US state abbreviation
UPDATE "clubs"
SET "country" = 'US'
WHERE "state" IN (
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
  'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
  'DC'
);

-- Set country for Madrid Comedy Lab
UPDATE "clubs"
SET "country" = 'Spain'
WHERE "id" = 1061;
