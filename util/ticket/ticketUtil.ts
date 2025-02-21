import { Ticket } from "@/objects/class/ticket/Ticket";

export function mapTickets(tickets: any[]) {
    return tickets ? tickets.map(ticket => ({
        price: ticket.price ? Number(ticket.price) : null,
        purchaseUrl: ticket.purchaseUrl,
        type: ticket.type,
        soldOut: ticket.soldOut
    })) : [];
}

export function formatTicketString(tickets: Ticket[]) {
    if (tickets.length === 1) {
        return `$${tickets[0].price.toString()}`;
    } else if (tickets.length > 1) {
        const prices = tickets.map(ticket => ticket.price).sort((a, b) => a - b);
        return `$${prices[0].toString()} - $${prices[prices.length - 1].toString()}`;
    } else {
        return '';
    }
}
