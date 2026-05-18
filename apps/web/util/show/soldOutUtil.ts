type TicketSoldOutState = {
    soldOut?: boolean | null;
};

const SOLD_OUT_TITLE_RE = /\bsold[\s-]*out\b/i;

export function titleHasSoldOutMarker(
    title: string | null | undefined,
): boolean {
    return SOLD_OUT_TITLE_RE.test(title ?? "");
}

export function computeShowSoldOut(
    title: string | null | undefined,
    tickets: TicketSoldOutState[] | null | undefined,
): boolean {
    if (titleHasSoldOutMarker(title)) {
        return true;
    }

    return (
        tickets !== undefined &&
        tickets !== null &&
        tickets.length > 0 &&
        tickets.every((ticket) => ticket.soldOut === true)
    );
}
