# Screenshot fixture artwork

These PNGs are original, fictional illustrations created for LaughTrack's
hermetic native screenshot fixtures. They are checked in so capture runs stay
offline, byte-for-byte reproducible, and independent of third-party CDNs.

The source prompts requested polished, square editorial artwork in four sets:

- fictional stand-up performer portraits;
- fictional comedy-club stage emblems;
- fictional comedy-show key art; and
- fictional podcast studio covers.

Every prompt prohibited text, copied logos, watermarks, celebrity likenesses,
and third-party branding. The generated images were resized to 640 by 640,
stripped of metadata, and checksummed in `fixture_server.py` and
`screenshots/catalog.json`.

The filenames are stable fixture identifiers rather than claims that the art
depicts the real person, venue, show, or podcast named by the corresponding
fixture. The artwork was generated specifically for this repository and may be
redistributed with the project as screenshot fixture material.
