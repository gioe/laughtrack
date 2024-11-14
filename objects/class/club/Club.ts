import { toSocialDataInterface } from "../../../util/socialData/mapper";
import { EntityType } from "../../enum";
import { Entity, SocialDataInterface, TagInterface } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { ClubDTO, ClubInterface } from "./club.interface";

export class Club implements ClubInterface {
    website: string;
    city: string;
    address: string;
    zipCode: string;
    socialData: SocialDataInterface;
    tags: TagInterface[];
    name: string;
    isFavorite: boolean;
    id: number;
    scrapingPageUrl: string;
    type: EntityType = EntityType.Club;
    bannerImageUrl: string;
    cardImageUrl: string;
    containedEntities: Entity[]

    constructor(input: ClubDTO) {
        this.website = input.website;
        this.city = input.city;
        this.address = input.address;
        this.zipCode = input.zip_code;
        this.containedEntities = input.dates !== undefined ? input.dates.map((date: ShowDTO) => new Show(date)) : [];
        this.socialData = input.social_data !== undefined ? toSocialDataInterface(input.social_data) : {};
        this.tags = [];
        this.name = input.name
        this.isFavorite = input.is_Favorite ?? false;
        this.id = input.id
        this.scrapingPageUrl = input.scraping_page_url
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/club/square/${input.name}.png`;
    }

    getShows(): Show[] {
        return this.containedEntities as Show[]
    }


}
