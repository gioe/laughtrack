import { Decimal } from "@prisma/client/runtime/library";

// Client
export interface TicketInterface {
    price: number;
    link: string;
}

// DB
export interface TicketDTO {
    price: Decimal | null;
    link: string | null;
}

