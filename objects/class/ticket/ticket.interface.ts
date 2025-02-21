import { Decimal } from "@prisma/client/runtime/library";

// Client
export interface TicketInterface {
    price: number;
    purchaseUrl: string | null;
    soldOut: boolean | null;
    type: string | null;
}

// DB
export interface TicketDTO {
    price: number | null;
    purchaseUrl: string | null;
    soldOut: boolean | null;
    type: string | null;
}
