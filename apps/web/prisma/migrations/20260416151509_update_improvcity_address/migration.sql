-- Update ImprovCity (club 786) address — was empty from bulk import
UPDATE clubs SET address = '138 W Main St, Tustin, CA 92780' WHERE id = 786;
