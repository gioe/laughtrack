import {
    Favoritable,
    ShowProvider,
    SocialDiscoverable,
    Taggable,
    TagDTO,
    Entity,
} from "../../interfaces";
import { ImageRepresentable } from "../../interfaces/imageRepresentable.interface";
import { SocialDataDTO } from "../../interfaces/socialData.interface";
import { ShowDTO } from "../show/show.interface";

// Client
export interface ComedianInterface
    extends ShowProvider,
    SocialDiscoverable,
    Taggable,
    Favoritable,
    ImageRepresentable, Entity { }


// DB
export interface ComedianDTO {
    name: string;
    id?: number
    uuid_id?: string;
    userId?: number;
    social_data?: SocialDataDTO;
    dates?: ShowDTO[];
    is_favorite?: boolean;
    tags?: TagDTO[]
}
