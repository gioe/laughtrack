import { Ticket } from "@/objects/class/ticket/Ticket";
import { TicketDTO } from "@/objects/class/ticket/ticket.interface";

type TicketPrice = number | string | { toNumber: () => number } | null;
type TicketSource = Omit<TicketDTO, "price"> & { price: TicketPrice };

export function mapTickets(tickets: TicketSource[]): TicketDTO[] {
    const val = tickets
        ? tickets.map((ticket) => ({
              price: mapTicketPrice(ticket.price),
              purchaseUrl: ticket.purchaseUrl,
              type: ticket.type,
              soldOut: ticket.soldOut,
          }))
        : [];

    return val;
}

function mapTicketPrice(price: TicketPrice): number | null {
    if (price == null) return null;
    if (typeof price === "number") return price;
    if (typeof price === "object" && typeof price.toNumber === "function") {
        return price.toNumber();
    }

    const numericPrice = Number(price);
    return Number.isFinite(numericPrice) ? numericPrice : null;
}

export function formatTicketString(tickets: Ticket[]) {
    const prices = tickets
        .map((ticket) => ticket.price)
        .filter((price): price is number => price != null)
        .sort((a, b) => a - b);

    if (prices.length === 0) {
        return "";
    }

    if (prices.length === 1) {
        return prices[0] == 0.0 ? "Free" : `$${prices[0].toString()}`;
    } else {
        const lowestPrice = prices[0];
        const highestPrice = prices[prices.length - 1];

        if (lowestPrice == 0.0 && highestPrice == 0.0) {
            return "Free";
        } else if (lowestPrice == 0.0) {
            return `Free - $${highestPrice.toString()}`;
        } else {
            return `$${lowestPrice.toString()} - $${highestPrice.toString()}`;
        }
    }
}
