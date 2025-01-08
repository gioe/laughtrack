import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { SocialData } from "../socialData/SocialData";
import { ClubDTO, ClubInterface } from "./club.interface";

export class Club implements ClubInterface {
    website: string;
    city: string;
    address: string;
    zipCode: string;
    socialData?: SocialData;
    tagIds: number[];
    name: string;
    isFavorite: boolean;
    id: number;
    type: EntityType = EntityType.Club;
    bannerImageUrl: string;
    cardImageUrl: string;
    containedEntities: Entity[]
    showCount?: number;

    constructor(input: ClubDTO) {
        this.website = input.website;
        this.city = input.city ?? ""
        this.address = input.address ?? ""
        this.zipCode = input.zipCode ?? ""
        this.containedEntities = input.dates !== undefined ? input.dates.map((date: ShowDTO) => new Show(date)) : [];
        this.socialData = input.social_data !== undefined ? new SocialData(input.social_data) : undefined;
        this.tagIds = input.tags ? input.tags : [];
        this.name = input.name
        this.isFavorite = input.is_Favorite ?? false;
        this.id = input.id
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/club/square/${input.name}.png`;
        this.showCount = input.show_count
    }

    getShows(): Show[] {
        return this.containedEntities as Show[]
    }


}
