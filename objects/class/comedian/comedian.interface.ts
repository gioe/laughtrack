import {
    Favoritable,
    Entity,
} from "../../interface";
import { SocialDataDTO } from "../socialData/socialData.interface";
import { ShowDTO } from "../show/show.interface";
import { TagDataDTO } from "../../interface/tag.interface";

// Client
export interface ComedianInterface
    extends

    Favoritable,
    Entity { }


// DB
export interface ComedianDTO {
    name: string;
    uuid?: string;
    id?: number
    userId?: number;
    social_data?: SocialDataDTO;
    dates?: ShowDTO[];
    is_favorite?: boolean;
    tags?: TagDataDTO[]
    show_count?: number
}

