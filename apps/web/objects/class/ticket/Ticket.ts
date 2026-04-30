import { TicketDTO, TicketInterface } from "./ticket.interface";

export class Ticket implements TicketInterface {
    price: number | null;
    purchaseUrl: string | null;
    soldOut: boolean | null;
    type: string | null;

    // Constructor
    constructor(input: TicketDTO) {
        this.price = input.price;
        this.purchaseUrl = input.purchaseUrl;
        this.soldOut = input.soldOut;
        this.type = input.type;
    }
    link?: string | null;
}
