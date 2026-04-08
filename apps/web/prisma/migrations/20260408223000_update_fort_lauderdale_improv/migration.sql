-- Update Dania Improv → Fort Lauderdale Improv with correct city/state
UPDATE "clubs"
SET
  "name" = 'Fort Lauderdale Improv',
  "city" = 'Dania Beach',
  "state" = 'FL',
  "address" = '177 N Pointe Dr, Dania Beach, FL 33004'
WHERE "id" = 53;
