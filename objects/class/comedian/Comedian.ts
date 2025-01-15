import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { ComedianDTO, ComedianInterface } from "./comedian.interface";
import { SocialData } from "../socialData/SocialData";

export class Comedian implements ComedianInterface {

    name: string;
    uuid?: string;
    socialData?: SocialData;
    tagIds: number[];
    isFavorite: boolean;
    id: number;
    type: EntityType = EntityType.Comedian;
    cardImageUrl: URL;
    containedEntities: Entity[]
    showCount?: number;
    isAlias?: boolean
    bannerImageUrl: URL | null;

    constructor(input: ComedianDTO) {
        this.name = input.name
        this.containedEntities = input.dates !== undefined ? input.dates.map((dto: ShowDTO) => new Show(dto)) : []
        this.socialData = input.social_data !== undefined ? new SocialData(input.social_data) : undefined;
        this.tagIds = input.tags ? input.tags : [];
        this.isFavorite = input.is_favorite ?? false
        this.id = input.id ?? 0
        this.showCount = input.show_count
        this.cardImageUrl = new URL(`/comedians/${input.name}.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`) ?? new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`);
        this.uuid = input.uuid
        this.isAlias = input.is_alias ?? false
    }
    fallbackImageUrl: URL;


    getDates() {
        return this.containedEntities as Comedian[]
    }

    getFirstName() {
        return this.name.split(" ")[0]
    }

    getLastName() {
        return this.name.split(" ")[1]
    }

}
