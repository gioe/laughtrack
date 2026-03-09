import { Favoritable, Entity } from "../../interface";
import { SocialDataDTO } from "../socialData/socialData.interface";
import { ShowDTO } from "../show/show.interface";

// Client
export interface ComedianInterface extends Favoritable, Entity {}

// DB
export interface ComedianDTO {
    name: string;
    imageUrl: string;
    uuid: string;
    id: number;
    userId?: number;
    social_data: SocialDataDTO;
    dates?: ShowDTO[];
    isFavorite?: boolean;
    tags?: number[];
    show_count: number;
    isAlias?: boolean;
    parentComedian?: ComedianDTO;
    lineupItems?: any[];
}

// Lightweight comedian shape used for show lineup items (no social_data or show_count required)
export type ComedianLineupDTO = Omit<
    ComedianDTO,
    "social_data" | "show_count"
> & {
    social_data?: SocialDataDTO;
    show_count?: number;
};

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
