import { TicketDTO, TicketInterface } from "./ticket.interface";
import { Prisma } from '@prisma/client'

export class Ticket implements TicketInterface {
    price: number;
    link: string | null;

    // Constructor
    constructor(input: TicketDTO) {
        this.price = input.price ? input.price.toNumber() : 0;
        this.link = input.link;
    }


    asTicketDTO = (): TicketDTO => {
        return {
            price: this.price ? new Prisma.Decimal(this.price) : new Prisma.Decimal(0),
            link: this.link
        };
    };
}
