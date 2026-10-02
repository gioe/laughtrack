# Gotham poster OCR fixtures

`main` and `spotlight` are public feed assets retrieved on 2026-10-01; their JSON files record the source URL and exact event time. `vintage` is the retained 2026-09-26 show 5509344 asset from the missing-lineups audit. Pixel hashes bind each captured Tesseract 5.5.3 TSV sequence to its image.

The parser supports these two caption layouts, not general event artwork. It reads only date, venue/room text and printed caption rectangles. Square poster dates are rotated -13 degrees; captions and branding are not rotated. Spotlight's small branding crop omits padding because padding confuses OCR. The JSON records actual OCR output, including noise; fixtures do not substitute corrected names.

Main Room is inferred only from the authoritative feed association when date, weekday, time and COMEDY CLUB branding match and the asset is unique across performances. Vintage requires explicit VINTAGE LOUNGE text. All candidate names must independently match one canonical database identity and pass deny-list suppression. Face images, title wording, and unreadable text never supply identities. Unnamed TBA slots remain unknown.

Deterministic tests replay captured TSV; optional installed-binary tests run actual Tesseract over these pixels. Historical dates are parsed directly and do not depend on the current clock.
