import { ShowDTO } from "@/objects/class/show/show.interface";

export interface ShowTagDTO {
    slug: string;
    name: string;
}

export interface ShowDetailDTO extends ShowDTO {
    // External ticketing / show-page URL (schema column: show_page_url).
    // Used as the CTA fallback when no ticket row exposes a purchase URL.
    showPageUrl: string;
    // PUBLIC-visibility tags only — ADMIN tags are filtered at the query
    // boundary so internal taxonomy can never leak through the API.
    tags?: ShowTagDTO[];
}

export interface ShowDetailResponse {
    show: ShowDetailDTO;
    relatedShows: ShowDTO[];
}
