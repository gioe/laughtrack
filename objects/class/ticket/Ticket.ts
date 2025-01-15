import { TicketDTO, TicketInterface } from "./ticket.interface";

export class Ticket implements TicketInterface {
    price: number;
    link: string | null;

    // Constructor
    constructor(input: TicketDTO) {
        this.price = input.price ? Number(input.price) : 0;
        this.link = input.link;
    }
}
