import { ShowDTO } from "@/objects/class/show/show.interface";

export interface ShowDetailDTO extends ShowDTO {
    // External ticketing / show-page URL (schema column: show_page_url).
    // Used as the CTA fallback when no ticket row exposes a purchase URL.
    showPageUrl: string;
    // URL slug for linking to /club/[slug] (encoded club name).
    clubSlug: string;
    // True when the show's date is before "now".
    isPast: boolean;
    // Internal — used by getShowDetailPageData to fetch related shows at the same club.
    clubId: number;
}

export interface ShowDetailResponse {
    show: ShowDetailDTO;
    relatedShows: ShowDTO[];
}
