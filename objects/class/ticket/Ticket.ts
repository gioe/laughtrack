import { TicketDTO, TicketInterface } from "./ticket.interface";


export class Ticket implements TicketInterface {
    price: number;
    link: string;

    // Constructor
    constructor(input: TicketDTO) {
        this.price = input.price;
        this.link = input.link;
    }


    asTicketDTO = (): TicketDTO => {
        return {
            price: this.price,
            link: this.link
        };
    };
}
