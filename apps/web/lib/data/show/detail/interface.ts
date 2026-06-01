import { ShowDTO, ShowTagDTO } from "@/objects/class/show/show.interface";

// Re-export so existing imports from "@/lib/data/show/detail/interface" keep
// resolving. ShowTagDTO now lives on the base ShowDTO since list/search
// responses also carry tags.
export type { ShowTagDTO };

export interface ShowDetailDTO extends ShowDTO {
    // External ticketing / show-page URL (schema column: show_page_url).
    // Used as the CTA fallback when no ticket row exposes a purchase URL.
    showPageUrl: string;
}

export interface ShowDetailResponse {
    show: ShowDetailDTO;
    relatedShows: ShowDTO[];
}
