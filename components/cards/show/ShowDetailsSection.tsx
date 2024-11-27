"use client";

import React from "react";
import moment from "moment";
import Link from "next/link";
import { Ticket } from "../../../objects/class/ticket/Ticket";
import LinkedImage from "../../image/link";
import { useSession } from "next-auth/react";

interface ShowCardProps {
    clubName?: string;
    showDate?: Date;
    scrapedDate?: Date;
    ticket: Ticket;
}

const ShowDetailsSection: React.FC<ShowCardProps> = ({
    clubName,
    showDate,
    scrapedDate,
    ticket,
}) => {
    const session = useSession();
    const showShowScrapeDate = session.data?.user.role == "admin";

    const dateObject = moment(new Date(showDate ?? new Date()));
    const scrapeDateObject = moment(scrapedDate);

    return (
        <div className="grid grid-cols-2 divide-x">
            <div className="flex flex-col items-center ml-5 mr-4 mb-5 mt-1">
                {/* {showShowScrapeDate && (
                    <h1 className="text-m ml-2 text-center">
                        {scrapeDateObject.format(
                            "dddd, MMMM Do YYYY, h:mm:ss a",
                        )}
                    </h1>
                )} */}
                <h4 className="text-xl ml-2 text-center">
                    {dateObject.format("LT")}
                </h4>
                <div className="relative h-20 w-20 align-middle">
                    <LinkedImage
                        destination={`/club/${clubName ?? ""}`}
                        imageUrl={`/images/club/square/${clubName ?? ""}.png`}
                        alt={clubName ?? "" + dateObject}
                    />
                </div>
                <h4 className="text-xl ml-2 text-center">{clubName ?? ""}</h4>
                <p className="text-m ml-2 text-center">
                    {dateObject.format("LL")}
                </p>
                <h1 className="text-center mt-8 text-sm">{`$${ticket.price.toString()}`}</h1>
                <Link
                    className="text-center text-sm underline"
                    href={ticket.link}
                >
                    <p className="text-m ml-2 text-center">Get tickets</p>
                </Link>
            </div>
        </div>
    );
};

export default ShowDetailsSection;
