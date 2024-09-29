import React from "react";
import { SearchResult } from "@/interfaces/searchResult.interface";
import { MiniComedianIcon } from "./MiniComedianIcon";
import { ComedianInterface } from "@/interfaces/comedian.interface";

interface SearchResultsInfoCardProps {
    result: SearchResult;
}

const SearchResultsInfoCard: React.FC<SearchResultsInfoCardProps> = ({
    result
}) => {
    const time = new Date(result.date_time).toLocaleTimeString();
    const date = new Date(result.date_time).toLocaleDateString();

    const description = `${time} at ${result.club_name} on ${date}`

    return (
        <div className="flex mt-3 py-7 px-2 pr-4 
        border-b cursor-pointer hover:opacity-80 
        hover:shadow-lg transition duration-200 rounded-lg 
        ease-out first:border-t bg-white">
            <div className="flex flex-col flex-grow pl-5">
                <h4 className="text-xl">{description}</h4>

                <div className="border-b w-10 p-2" />

                <section className="max-w-7xl mt-1 p-1 bg-white rounded-t-lg">
                <h4 className="text-m">Featuring</h4>
                <div className="flex space-x-3 overflow-scroll scrollbar-hide p-3 -ml-3 ">
                        {result.lineup
                            .sort((a, b) => b.popularity_score - a.popularity_score)
                            .map((item: ComedianInterface) => {
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

export default SearchResultsInfoCard;