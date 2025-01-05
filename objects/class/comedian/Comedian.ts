import { EntityType } from "../../enum";
import {
    removeBadWhiteSpace,
    capitalized,
    isUpperCase,
    isLowerCase
} from "../../../util/primatives/stringUtil";
import { Entity } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import { ComedianDTO, ComedianInterface } from "./comedian.interface";
import { generateHash } from "../../../util/hashUtil";
import { SocialData } from "../socialData/SocialData";

export class Comedian implements ComedianInterface {

    name: string;
    uuid?: string;
    socialData?: SocialData;
    tagIds: number[];
    isFavorite: boolean;
    id: number;
    type: EntityType = EntityType.Comedian;
    bannerImageUrl: string;
    cardImageUrl: string;
    containedEntities: Entity[]
    showCount?: number;
    isAlias?: boolean

    constructor(input: ComedianDTO) {
        this.name = this.normalizeName(input.name);
        this.containedEntities = input.dates !== undefined ? input.dates.map((dto: ShowDTO) => new Show(dto)) : []
        this.socialData = input.social_data !== undefined ? new SocialData(input.social_data) : undefined;
        this.tagIds = input.tags ? input.tags : [];
        this.isFavorite = input.is_favorite ?? false
        this.id = input.id ?? 0
        this.showCount = input.show_count
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/comedian/square/${input.name}.png`;
        this.uuid = input.uuid
        this.isAlias = input.is_alias ?? false
    }

    // Sometimes we receive names from websites that are entirely uppercase or lowercase. These are the only times when we want to insure
    // proper capitalization. Otherwise leave it alone.
    normalizeName = (name: string): string => {
        const cleanString = removeBadWhiteSpace(name);

        if (isUpperCase(cleanString) || isLowerCase(cleanString)) {
            return capitalized(cleanString)
        }
        return cleanString
    };

    asComedianDTO = (): ComedianDTO => {
        return {
            name: this.name,
            uuid: this.hashName()
        };
    };

    hashName() {
        return generateHash(this.name)
    }

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
