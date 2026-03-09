"use client";

import React, { useEffect } from "react";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { FullRoundedButton } from "@/ui/components/button/rounded/full";
import { Show } from "@/objects/class/show/Show";
import ShowCardHeader from "@/ui/components/cards/show/header";
import LineupGrid from "@/ui/components/lineup";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { Divider } from "../../divider";

const seenShowIds = new Set<number>();

interface ShowCardProps {
    show: ShowDTO;
}

const ShowCard: React.FC<ShowCardProps> = ({ show }: ShowCardProps) => {
    const { mv, mp } = useMotionProps();
    const parsedShow = new Show(show);
    const stillOnSale =
        parsedShow.tickets.filter((ticket) => !ticket.soldOut).length > 0;
    // Read before useEffect so first render always animates, remounts skip it
    const alreadySeen = seenShowIds.has(show.id);

    useEffect(() => {
        seenShowIds.add(show.id);
    }, [show.id]);

    return (
        <motion.div
            className="p-2 sm:p-6 bg-gradient-to-br from-[#FDF8EF] to-[#F5E6D3] overflow-hidden
                rounded-xl w-full shadow-md hover:shadow-xl border border-white/20"
            initial={alreadySeen ? false : { opacity: 0, y: mv(20) }}
            whileInView={{ opacity: 1, y: 0 }}
            whileHover={mp({ scale: 1.02, transition: { duration: 0.15 } })}
            viewport={{ once: true }}
            transition={{
                duration: mv(0.5),
                ease: "easeOut",
            }}
        >
            <div className="flex flex-col lg:flex-row gap-2 sm:gap-4">
                <div className="flex-1 lg:w-[35%] flex flex-col gap-2 sm:gap-4">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 sm:gap-4">
                        <div className="flex-1">
                            <ShowCardHeader show={parsedShow} />
                        </div>

                        {parsedShow.tickets.length > 0 && (
                            <div className="sm:self-start">
                                <FullRoundedButton
                                    href={parsedShow.tickets[0].purchaseUrl}
                                    label={
                                        stillOnSale ? "Get Tickets" : "Sold Out"
                                    }
                                    color={
                                        stillOnSale ? "bg-copper" : "bg-red-500"
                                    }
                                />
                            </div>
                        )}
                    </div>

                    {parsedShow.lineup.length > 0 && (
                        <div className="lg:hidden">
                            <Divider />
                            <div className="pt-2 sm:pt-4">
                                <LineupGrid lineup={parsedShow.lineup} />
                            </div>
                        </div>
                    )}
                </div>

                {parsedShow.lineup.length > 0 && (
                    <div className="hidden lg:block lg:w-[65%]">
                        <LineupGrid lineup={parsedShow.lineup} />
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default ShowCard;
