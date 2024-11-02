import { Comedian } from "./Comedian";
import { CreateShowDTO, ShowInput, CreateComedianDTO } from "../interfaces";

export class Show {
    lineup: Comedian[];
    dateTime: Date;
    ticketLink: string;
    name: string;
    price: string;
    clubId: number;

    constructor(showInput: ShowInput) {
        this.lineup = showInput.lineup;
        this.dateTime = showInput.dateTime;
        this.ticketLink = showInput.ticketLink;
        this.name = showInput.name;
        this.price = showInput.price;
        this.clubId = showInput.clubId;
    }

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

    asCreateShowDTO = (): CreateShowDTO => {
        return {
            club_id: this.clubId,
            date_time: this.dateTime,
            ticket_link: this.ticketLink,
            name: this.name,
            price: this.price,
        };
    };

    asCreateComedianDTOArray = (): CreateComedianDTO[] => {
        return this.lineup.map((comedian: Comedian) =>
            comedian.asCreateComedianDTO(),
        );
    };
}
