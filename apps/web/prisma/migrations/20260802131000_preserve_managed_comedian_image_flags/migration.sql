UPDATE comedians AS c
SET has_image = TRUE
WHERE c.has_image = FALSE
  AND EXISTS (
      SELECT 1
      FROM comedian_image_assets AS a
      WHERE a.comedian_id = c.id
        AND a.is_active = TRUE
        AND a.avatar_path IS NOT NULL
  );
