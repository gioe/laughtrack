import { toSocialDataInterface } from "../../../util/socialData/mapper";
import { EntityType } from "../../enum";
import {
    removeBadWhiteSpace,
    capitalized,
    removeNonAlphanumeric,
} from "../../../util/primatives/stringUtil";
import { Entity, SocialDataInterface, TagInterface } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { ComedianDTO, ComedianInterface } from "./comedian.interface";
import { generateHash } from "../../../util/hashUtil";
export class Comedian implements ComedianInterface {

    name: string;
    uuid?: string;
    socialData: SocialDataInterface;
    tags: TagInterface[];
    isFavorite: boolean;
    id: number;
    type: EntityType = EntityType.Comedian;
    bannerImageUrl: string;
    cardImageUrl: string;
    containedEntities: Entity[]

    constructor(input: ComedianDTO) {
        const cleanString = removeBadWhiteSpace(input.name);
        this.name = capitalized(cleanString);
        this.containedEntities = input.dates !== undefined ? input.dates.map((dto: ShowDTO) => new Show(dto)) : []
        this.socialData = input.social_data !== undefined ? toSocialDataInterface(input.social_data) : {};
        this.tags = []
        this.isFavorite = input.is_favorite ?? false
        this.id = input.id ?? 0
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/comedian/square/${input.name}.png`;
        this.uuid = input.uuid
    }
    dates: Show[];

    asComedianDTO = (): ComedianDTO => {
        return {
            name: this.name,
            uuid: this.hashName()
        };
    };

    hashName() {
        const normalizedName = removeNonAlphanumeric(this.name).toLocaleLowerCase()
        return generateHash(normalizedName)
    }

    getDates() {
        return this.containedEntities as Comedian[]
    }

}
