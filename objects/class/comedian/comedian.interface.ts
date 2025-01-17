import {
    Favoritable,
    Entity,
} from "../../interface";
import { SocialDataDTO } from "../socialData/socialData.interface";
import { ShowDTO } from "../show/show.interface";

// Client
export interface ComedianInterface
    extends
    Favoritable,
    Entity { }


// DB
export interface ComedianDTO {
    name: string;
    imageUrl: string
    uuid?: string;
    id?: number
    userId?: number;
    social_data?: SocialDataDTO;
    dates?: ShowDTO[];
    is_favorite?: boolean;
    tags?: number[]
    show_count?: number
    is_alias?: boolean
}

export interface UpdateComedianDTO {
    name: string;
    instagram_account: string,
    instagram_followers: number,
    tiktok_account: string,
    tiktok_followers: number,
    youtube_account: string,
    youtube_followers: number,
    website: string
    linktree: string,
}
