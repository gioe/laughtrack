import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Comedian } from "../comedian/Comedian";
import { ComedianDTO } from "../comedian/comedian.interface";
import { ShowDTO, ShowInterface } from "./show.interface";
import { Ticket } from "../ticket/Ticket";
import { SocialData } from "../socialData/SocialData";

export class Show implements ShowInterface {
    // Properties
    name: string;
    date: Date;
    socialData?: SocialData;
    popularityScore?: number | undefined;
    clubName?: string | undefined;
    clubId: number;
    ticket: Ticket;
    tagIds: number[];
    id: number;
    type: EntityType = EntityType.Show;
    containedEntities: Entity[]
    lineup: Comedian[]
    isFavorite: boolean;
    lastScrapedDate?: Date;
    description?: string;
    bannerImageUrl: URL | null;
    cardImageUrl: URL;
    fallbackImageUrl = new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`);

    // Constructor
    constructor(input: ShowDTO) {
        this.name = input.name ?? "";
        this.date = input.date;
        this.socialData = input.social_data !== undefined ? new SocialData(input.social_data) : undefined;
        this.containedEntities = input.lineup ? input.lineup.map((item: ComedianDTO) => new Comedian(item)) : []
        this.lineup = input.lineup ? input.lineup.map((item: ComedianDTO) => new Comedian(item)) : []
        this.clubName = input.club_name;
        this.ticket = new Ticket(input.ticket)
        this.tagIds = input.tags ? input.tags : [];
        this.id = input.id ?? 0
        this.clubId = input.club_id ? Number(input.club_id) : 0
        this.lastScrapedDate = input.last_scraped_date
        this.description = input.description
    }


    overrideDate = (date: string): void => {
        const providedDate = new Date(date);
        this.date = new Date(
            providedDate.getUTCFullYear(),
            providedDate.getUTCMonth(),
            providedDate.getUTCDate(),
            this.date.getHours(),
            this.date.getMinutes(),
            this.date.getSeconds(),
        );
    };

}
