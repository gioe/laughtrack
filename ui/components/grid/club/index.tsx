"use server";

import { ClubDTO } from "@/objects/class/club/club.interface";
import { Club } from "@/objects/class/club/Club";
import ClubSearchCard from "../../cards/club/search";

interface ClubGridProps {
    contentString: string;
}
const ClubGrid = ({ contentString }: ClubGridProps) => {
    const clubs = JSON.parse(contentString) as ClubDTO[];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4 mx-28 gap-x-20 bg-red-800">
            {clubs.map((dto) => {
                const club = new Club(dto);
                return (
                    <ClubSearchCard
                        key={club.name}
                        entity={JSON.stringify(club)}
                    />
                );
            })}
        </div>
    );
};

export default ClubGrid;
