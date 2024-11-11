import { toSocialDataInterface } from "../../../util/socialData/mapper";
import { EntityType } from "../../../util/enum";
import { SocialDataInterface, TagInterface } from "../../interfaces";
import { Comedian } from "../comedian/Comedian";
import { ComedianDTO } from "../comedian/comedian.interface";
import { ShowDTO, ShowInterface } from "./show.interface";
import { Ticket } from "../ticket/Ticket";

export class Show implements ShowInterface {
    // Properties
    name: string;
    date: Date;
    socialData: SocialDataInterface;
    lineup: Comedian[];
    popularityScore?: number | undefined;
    clubName?: string | undefined;
    clubId: number;
    ticket: Ticket;
    tags: TagInterface[];
    id: number;
    type: EntityType = EntityType.Show;
    bannerImageUrl: string;
    cardImageUrl: string;
    scraped?: Date;

    // Constructor
    constructor(input: ShowDTO) {
        this.name = input.name;
        this.date = input.date;
        this.socialData = input.social_data !== undefined ? toSocialDataInterface(input.social_data) : {};
        this.lineup = input.lineup !== undefined ? input.lineup.map((item: ComedianDTO) => new Comedian(item)) : []
        this.clubName = input.club_name;
        this.ticket = new Ticket(input.ticket)
        this.tags = input.tags ?? []
        this.id = input.id ?? 0
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/show}/square/${input.name}.png`;
        this.clubId = input.club_id
        this.scraped = input.scraped
    }
    price: number;
    ticketLink: string;
    isFavorite: boolean;


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
            scraped: new Date()
        };
    };

    asComedianDTOArray = (): ComedianDTO[] => {
        return this.lineup.map((comedian: Comedian) =>
            comedian.asComedianDTO(),
        );
    };


}
