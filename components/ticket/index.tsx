"use client";

import { Ticket } from "../../objects/class/ticket/Ticket";
import { FullRoundedButton } from "../button/rounded/full";
import { useRouter } from "next/navigation";

interface TicketDetailProps {
    ticket: Ticket;
}

const TicketDetail = ({ ticket }: TicketDetailProps) => {
    const router = useRouter();

    const linkToTicketPurchase = (url: string) => {
        router.push(url);
    };

    return (
        <div className="flex flex-col items-center gap-3">
            <h1 className="text-center text-xl text-pine-tree font-fjalla">{`$${ticket.price.toString()}`}</h1>
            <FullRoundedButton
                label="Buy tickets"
                handleClick={() => {
                    linkToTicketPurchase(ticket.link);
                }}
            />
        </div>
    );
};

export default TicketDetail;
