// Stage treatment gradients — the comedy-club "Brick & Spotlight" chrome that
// originated on ShowCard. Exported as named constants so other surfaces
// (e.g. club detail) can reuse the same stage language. Apply via inline
// `style={{ background: ... }}` / `style={{ backgroundImage: ... }}` — these
// are full CSS gradient values, not Tailwind classes.

// Faint exposed-brick texture for the card surface — two repeating-line layers
// at low alpha read as masonry without competing with the content.
export const BRICK_TEXTURE =
    "repeating-linear-gradient(0deg, rgba(255,255,255,0.045) 0px, rgba(255,255,255,0.045) 1px, transparent 1px, transparent 22px)," +
    "repeating-linear-gradient(90deg, rgba(255,255,255,0.035) 0px, rgba(255,255,255,0.035) 1px, transparent 1px, transparent 46px)";

// Warm spotlight wash falling across the card from the upper-right (toward the
// visual panel), so the whole card reads as a lit stage rather than a flat box.
export const CARD_SPOTLIGHT =
    "radial-gradient(62% 70% at 80% -10%, rgba(247,231,206,0.12), rgba(184,115,51,0.05) 42%, transparent 72%)";

// Subtle warm spotlight wash from the top edge — the compact echo of the
// standard density's Brick & Spotlight stage treatment.
export const COMPACT_CARD_SPOTLIGHT =
    "radial-gradient(85% 65% at 50% -12%, rgba(247,231,206,0.10), rgba(184,115,51,0.04) 45%, transparent 70%)";

// Backdrop for the visual panel: a single spotlight cone from above + a copper
// floor pool below over a warm near-black, evoking a comedy-club stage.
export const STAGE_BACKDROP =
    "radial-gradient(120% 82% at 50% -14%, rgba(247,231,206,0.20), rgba(247,231,206,0.05) 38%, transparent 66%)," +
    "radial-gradient(72% 36% at 50% 106%, rgba(184,115,51,0.18), transparent 70%)," +
    "linear-gradient(180deg, #1c140e 0%, #100b08 100%)";
