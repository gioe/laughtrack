import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Show } from "../show/Show";
import { ShowDTO } from "../show/show.interface";
import {
    ComedianDTO,
    ComedianInterface,
    ComedianLineupDTO,
} from "./comedian.interface";
import { SocialData } from "../socialData/SocialData";

export class Comedian implements ComedianInterface {
    name: string;
    uuid: string;
    socialData?: SocialData;
    isFavorite: boolean;
    id: number;
    type: EntityType = EntityType.Comedian;
    imageUrl: string;
    hasImage: boolean;
    containedEntities: Entity[];
    showCount?: number;
    coAppearances?: number;
    isAlias?: boolean;

    constructor(input: ComedianDTO | ComedianLineupDTO) {
        this.name = input.name;
        this.containedEntities =
            "dates" in input && input.dates !== undefined
                ? input.dates.map((dto: ShowDTO) => new Show(dto))
                : [];
        this.socialData = input.social_data
            ? new SocialData(input.social_data)
            : undefined;
        this.isFavorite = input.isFavorite ?? false;
        this.id = input.id;
        this.showCount = input.show_count;
        this.coAppearances = (input as ComedianDTO).co_appearances;
        this.imageUrl = input.imageUrl;
        this.hasImage = input.hasImage ?? Boolean(input.imageUrl);
        this.uuid = input.uuid;
        this.isAlias = input.isAlias ?? false;
    }
}
