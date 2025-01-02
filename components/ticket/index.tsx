"use client";

import Link from "next/link";
import { Ticket } from "../../objects/class/ticket/Ticket";

interface TicketDetailProps {
    ticket: Ticket;
}

const TicketDetail = ({ ticket }: TicketDetailProps) => {
    return (
        <div>
            <h1 className="text-center text-m text-pine-tree font-fjalla">{`$${ticket.price.toString()}`}</h1>
            <Link className="text-sm text-center underline" href={ticket.link}>
                <p className="font-fjalla text-copper text-center">
                    Get tickets
                </p>
            </Link>
        </div>
    );
};

export default TicketDetail;
