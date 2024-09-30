import React from "react";
import { LineupItemInterface, ShowDetailsInterface, ShowInterface } from "@/interfaces/show.interface";
import MiniComedianIcon from "./MiniComedianIcon";
import moment from "moment";

interface ShowInfoCardProps {
    show: ShowDetailsInterface;
}

const ShowInfoCard: React.FC<ShowInfoCardProps> = ({
    show
}) => {

    const dateObject = moment(new Date(show.dateTime));

    console.log(moment(dateObject))
    const description = `${dateObject.format('LT')} at ${show.club.name} in ${show.city} on ${dateObject.format('LL')}`


    return (
        <div className="flex mt-3 py-7 px-2 pr-4 
        border-b cursor-pointer hover:opacity-80 
        hover:shadow-lg transition duration-200 rounded-lg 
        ease-out first:border-t bg-white">
            <div className="flex flex-col flex-grow pl-5">
                <h4 className="text-xl">{description}</h4>

                <div className="border-b w-10 p-2" />

                <section className="max-w-7xl mt-1 p-1 bg-white rounded-t-lg">
                <h4 className="text-m">With</h4>
                <div className="flex space-x-3 overflow-scroll scrollbar-hide p-3 -ml-3 ">
                        {show.lineup
                            .sort((a, b) => b.popularityScore - a.popularityScore)
                            .map((item: LineupItemInterface) => {
                                return (
                                    <MiniComedianIcon key={item.name} comedian={item}  />
                                )
                            })}
                    </div>
                </section>
            </div>

        </div>
    )
}

export default ShowInfoCard;