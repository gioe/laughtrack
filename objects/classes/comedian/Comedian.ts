import { toSocialDataInterface } from "../../../util/socialData/mapper";
import { EntityType } from "../../../util/enum";
import {
    removeBadWhiteSpace,
    capitalized,
} from "../../../util/primatives/stringUtil";
import { SocialDataInterface, TagInterface } from "../../interfaces";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { ComedianDTO, ComedianInterface } from "./comedian.interface";
export class Comedian implements ComedianInterface {

    name: string;
    uuid: string;
    dates: Show[];
    socialData: SocialDataInterface;
    tags: TagInterface[];
    isFavorite: boolean;
    id: number;
    type: EntityType = EntityType.Comedian;
    bannerImageUrl: string;
    cardImageUrl: string;

    constructor(input: ComedianDTO) {
        const cleanString = removeBadWhiteSpace(input.name);
        this.name = capitalized(cleanString);
        this.dates = input.dates !== undefined ? input.dates.map((dto: ShowDTO) => new Show(dto)) : []
        this.socialData = input.social_data !== undefined ? toSocialDataInterface(input.social_data) : {};
        this.tags = []
        this.isFavorite = input.is_favorite ?? false
        this.id = input.id ?? 0
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/${EntityType.Comedian.valueOf()}/square/${input.name}.png`;
        this.uuid = input.uuid
    }

    asComedianDTO = (): ComedianDTO => {
        return {
            name: this.name,
            uuid: this.uuid,
        };
    };
}
