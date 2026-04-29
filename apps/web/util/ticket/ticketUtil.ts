import { Ticket } from "@/objects/class/ticket/Ticket";

export function mapTickets(tickets: any[]) {
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

function mapTicketPrice(price: any): number | null {
    if (price == null) return null;
    if (typeof price === "number") return price;
    if (typeof price.toNumber === "function") return price.toNumber();

    const numericPrice = Number(price);
    return Number.isFinite(numericPrice) ? numericPrice : null;
}

export function formatTicketString(tickets: Ticket[]) {
    if (tickets.length === 1) {
        return tickets[0].price == 0.0
            ? "Free"
            : `$${tickets[0].price.toString()}`;
    } else if (tickets.length > 1) {
        const prices = tickets
            .map((ticket) => ticket.price)
            .sort((a, b) => a - b);
        const lowestPrice = prices[0];
        const highestPrice = prices[prices.length - 1];

        if (lowestPrice == 0.0 && highestPrice == 0.0) {
            return "Free";
        } else if (lowestPrice == 0.0) {
            return `Free - $${highestPrice.toString()}`;
        } else {
            return `$${lowestPrice.toString()} - $${highestPrice.toString()}`;
        }
    } else {
        return "";
    }
}
