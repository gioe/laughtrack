import { toSocialDataInterface } from "../../../util/domainModels/socialData/mapper";
import { EntityType } from "../../../util/enum";
import { SocialDataInterface, TagInterface } from "../../interfaces";
import { Comedian } from "../comedian/Comedian";
import { ComedianDTO } from "../comedian/comedian.interface";
import { ShowDTO, ShowInterface } from "./show.interface";

export class Show implements ShowInterface {
    // Properties
    name: string;
    dateTime: Date;
    socialData: SocialDataInterface;
    lineup: Comedian[];
    popularityScore?: number | undefined;
    clubName?: string | undefined;
    clubId: number;
    price: number;
    ticketLink: string;
    tags: TagInterface[];
    id: number;
    type: EntityType = EntityType.Show;
    bannerImageUrl: string;
    cardImageUrl: string;

    // Constructor
    constructor(input: ShowDTO) {
        this.name = input.name;
        this.dateTime = input.date_time;
        this.socialData = input.social_data !== undefined ? toSocialDataInterface(input.social_data) : {};
        this.lineup = input.lineup !== undefined ? input.lineup.map((item: ComedianDTO) => new Comedian(item)) : []
        this.clubName = input.club_name;
        this.price = Number(input.price);
        this.ticketLink = input.ticket_link;
        this.tags = input.tags ?? []
        this.id = input.id ?? 0
        this.bannerImageUrl = `/images/banners/${input.name}.png`
        this.cardImageUrl = `/images/${EntityType.Show.valueOf()}/square/${input.name}.png`;
        this.clubId = input.club_id
    }
    isFavorite: boolean;


    overrideDate = (date: string): void => {
        const providedDate = new Date(date);
        this.dateTime = new Date(
            providedDate.getUTCFullYear(),
            providedDate.getUTCMonth(),
            providedDate.getUTCDate(),
            this.dateTime.getHours(),
            this.dateTime.getMinutes(),
            this.dateTime.getSeconds(),
        );
    };

    asShowDTO = (): ShowDTO => {
        return {
            club_id: this.clubId,
            date_time: this.dateTime,
            ticket_link: this.ticketLink,
            name: this.name,
            price: this.price.toString(),
        };
    };

    asComedianDTOArray = (): ComedianDTO[] => {
        return this.lineup.map((comedian: Comedian) =>
            comedian.asComedianDTO(),
        );
    };


}
