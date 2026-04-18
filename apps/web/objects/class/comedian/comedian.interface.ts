import { Favoritable, Entity } from "../../interface";
import { SocialDataDTO } from "../socialData/socialData.interface";
import { ShowDTO } from "../show/show.interface";

export type { ComedianLineupDTO } from "./comedianLineup.interface";

// Client
export interface ComedianInterface extends Favoritable, Entity {}

// DB
export interface ComedianDTO {
    name: string;
    imageUrl: string;
    hasImage?: boolean;
    uuid: string;
    id: number;
    userId?: number;
    social_data: SocialDataDTO;
    dates?: ShowDTO[];
    isFavorite?: boolean;
    show_count: number;
    co_appearances?: number;
    isAlias?: boolean;
    parentComedian?: ComedianDTO;
    lineupItems?: any[];
    bio?: string | null;
}

export interface UpdateComedianDTO {
    name: string;
    instagram_account: string;
    instagram_followers: number;
    tiktok_account: string;
    tiktok_followers: number;
    youtube_account: string;
    youtube_followers: number;
    website: string;
    linktree: string;
}
