import { ShowDTO } from "@/objects/class/show/show.interface";

export interface ShowDetailDTO extends ShowDTO {
    // External ticketing / show-page URL (schema column: show_page_url).
    // Used as the CTA fallback when no ticket row exposes a purchase URL.
    showPageUrl: string;
}

export interface ShowDetailResponse {
    show: ShowDetailDTO;
    relatedShows: ShowDTO[];
}
