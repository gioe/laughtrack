import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { SocialData } from "../socialData/SocialData";
import { ClubDTO, ClubInterface } from "./club.interface";

export class Club implements ClubInterface {
    id: number;
    website: string;
    city: string;
    address: string;
    zipCode: string;
    socialData?: SocialData;
    tagIds: number[];
    name: string;
    isFavorite: boolean;
    type: EntityType = EntityType.Club;
    bannerImageUrl: URL | null;
    cardImageUrl: URL | null;;
    containedEntities: Entity[]
    showCount?: number;
    count?: number
    fallbackImageUrl = new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`);

    constructor(input: ClubDTO) {
        this.website = input.website ?? ""
        this.city = input.city ?? ""
        this.address = input.address ?? ""
        this.zipCode = input.zipCode ?? ""
        this.containedEntities = input.dates !== undefined ? input.dates.map((date: ShowDTO) => new Show(date)) : [];
        this.socialData = input.social_data !== undefined ? new SocialData(input.social_data) : undefined;
        this.tagIds = input.tags ? input.tags : [];
        this.name = input.name ?? ""
        this.isFavorite = input.is_Favorite ?? false;
        this.id = input.id ?? 0
        this.cardImageUrl = new URL(`/clubs/${input.name}.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`);
        this.showCount = input.show_count
    }

    getShows(): Show[] {
        return this.containedEntities as Show[]
    }


}
