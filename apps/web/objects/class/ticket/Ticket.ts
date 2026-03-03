import { TicketDTO, TicketInterface } from "./ticket.interface";

export class Ticket implements TicketInterface {
    price: number;
    purchaseUrl: string | null;
    soldOut: boolean | null;
    type: string | null;

    // Constructor
    constructor(input: TicketDTO) {
        this.price = input.price ? input.price : 0;
        this.purchaseUrl = input.purchaseUrl;
        this.soldOut = input.soldOut;
        this.type = input.type;
    }
    link: string | null;
}
