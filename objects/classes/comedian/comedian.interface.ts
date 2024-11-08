import {
    Favoritable,
    ShowProvider,
    TagDTO,
    Entity,
} from "../../interfaces";
import { SocialDataDTO } from "../../interfaces/socialData.interface";
import { ShowDTO } from "../show/show.interface";

// Client
export interface ComedianInterface
    extends ShowProvider,
    Favoritable,
    Entity { }


// DB
export interface ComedianDTO {
    name: string;
    uuid: string;
    id?: number
    userId?: number;
    social_data?: SocialDataDTO;
    dates?: ShowDTO[];
    is_favorite?: boolean;
    tags?: TagDTO[]
}
