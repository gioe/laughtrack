export type TicketClickSourceSurface =
    | "show_detail"
    | "show_card"
    | "compact_show_card";

interface TrackTicketClickInput {
    showId: number;
    clubId: number;
    destinationUrl: string;
    sourceSurface: TicketClickSourceSurface;
}

export async function trackTicketClick(
    input: TrackTicketClickInput,
): Promise<void> {
    try {
        const body = {
            ...input,
            deviceMetadata: {
                platform: "web",
                language: navigator.language,
                viewport:
                    typeof window === "undefined"
                        ? undefined
                        : {
                              width: window.innerWidth,
                              height: window.innerHeight,
                          },
            },
        };

        if (navigator.sendBeacon) {
            const sent = navigator.sendBeacon(
                "/api/v1/ticket-clicks",
                new Blob([JSON.stringify(body)], {
                    type: "application/json",
                }),
            );
            if (sent) return;
        }

        await fetch("/api/v1/ticket-clicks", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(body),
            keepalive: true,
        });
    } catch {
        // Ticket navigation must not depend on analytics availability.
    }
}
