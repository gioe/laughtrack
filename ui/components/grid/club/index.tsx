"use server";

import { ClubDTO } from "@/objects/class/club/club.interface";
import { Club } from "@/objects/class/club/Club";
import ClubSearchCard from "../../cards/club/card/search";

interface ClubGridProps {
    contentString: string;
}
const ClubGrid = ({ contentString }: ClubGridProps) => {
    const clubs = JSON.parse(contentString) as ClubDTO[];
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-[50px] ml-20 mr-20 mb-10 mt-4">
            {clubs.map((dto) => {
                const club = new Club(dto);
                return (
                    <ClubSearchCard
                        key={dto.name}
                        entity={JSON.stringify(club)}
                    />
                );
            })}
        </div>
    );
};

export default ClubGrid;
