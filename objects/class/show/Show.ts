import { EntityType } from "../../enum";
import { Entity } from "../../interface";
import { Comedian } from "../comedian/Comedian";
import { ComedianDTO } from "../comedian/comedian.interface";
import { ShowDTO, ShowInterface } from "./show.interface";
import { Ticket } from "../ticket/Ticket";
import { SocialData } from "../socialData/SocialData";
import { capitalized, isLowerCase, isUpperCase, removeBadWhiteSpace } from "../../../util/primatives/stringUtil";

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
    bannerImageUrl: string;
    cardImageUrl: string;
    containedEntities: Entity[]
    isFavorite: boolean;
    lastScrapedDate?: Date;
    description?: string;

    // Constructor
    constructor(input: ShowDTO) {
        this.name = this.normalizeName(input.name);
        this.date = input.date;
        this.socialData = input.social_data !== undefined ? new SocialData(input.social_data) : undefined;
        this.containedEntities = input.lineup ? input.lineup.map((item: ComedianDTO) => new Comedian(item)) : []
        this.clubName = input.club_name;
        this.ticket = new Ticket(input.ticket)
        this.tagIds = input.tags ? input.tags : [];
        this.id = input.id ?? 0
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/show}/square/${input.name}.png`;
        this.clubId = input.club_id
        this.lastScrapedDate = input.last_scraped_date
        this.description = input.description
    }


    normalizeName = (name: string): string => {
        const cleanString = removeBadWhiteSpace(name);
        if (isUpperCase(cleanString) || isLowerCase(cleanString)) {
            return capitalized(cleanString)
        }
        return cleanString
    };

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

    asShowDTO = (): ShowDTO => {
        return {
            club_id: this.clubId,
            date: this.date,
            ticket: this.ticket.asTicketDTO(),
            name: this.name,
            last_scraped_date: this.lastScrapedDate,
            description: this.description
        };
    };

    asComedianDTOArray = (): ComedianDTO[] => {
        return this.containedEntities.map((comedian: Comedian) =>
            comedian.asComedianDTO(),
        );
    };

}
