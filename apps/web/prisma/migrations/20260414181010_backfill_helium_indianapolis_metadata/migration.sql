-- Backfill website, address, and zip_code for Helium Comedy Club - Indianapolis (club 139)
UPDATE "Club"
SET
  website = 'https://indianapolis.heliumcomedy.com',
  address = '10 W. Georgia St., Indianapolis, IN 46225',
  zip_code = '46225'
WHERE id = 139;
