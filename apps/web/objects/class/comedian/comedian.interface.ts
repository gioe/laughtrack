import { Favoritable, Entity } from "../../interface";
import { SocialDataDTO } from "../socialData/socialData.interface";
import { ShowDTO } from "../show/show.interface";
import { ComedianLineupItemDTO } from "./comedianLineup.interface";
import { PodcastAppearanceDTO } from "./podcastAppearance.interface";

export type { ComedianLineupDTO } from "./comedianLineup.interface";

// Client
export interface ComedianInterface extends Favoritable, Entity {}

// Derived "home base" for a comedian. Any field may be null when the
// scraper has not resolved a home location yet, so consumers must fall
// back gracefully rather than assume the values are present.
export interface ComedianHomeLocationDTO {
    city: string | null;
    state: string | null;
    country: string | null;
    club: { id: number; name: string } | null;
}

// DB
export interface ComedianDTO {
    name: string;
    imageUrl: string;
    hasImage?: boolean;
    uuid: string;
    id: number;
    userId?: number;
    socialData: SocialDataDTO;
    dates?: ShowDTO[];
    isFavorite?: boolean;
    showCount: number;
    coAppearances?: number;
    isAlias?: boolean;
    parentComedian?: ComedianDTO;
    lineupItems?: ComedianLineupItemDTO[];
    podcastAppearances?: PodcastAppearanceDTO[];
    homeLocation?: ComedianHomeLocationDTO;
}

export interface UpdateComedianDTO {
    name: string;
    instagramAccount: string;
    instagramFollowers: number;
    tiktokAccount: string;
    tiktokFollowers: number;
    youtubeAccount: string;
    youtubeFollowers: number;
    website: string;
    linktree: string;
}
