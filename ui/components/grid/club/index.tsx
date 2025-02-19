"use server";

import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubSearchCard from "../../cards/club/search";

interface ClubGridProps {
    clubs: ClubDTO[];
}
const ClubGrid = ({ clubs }: ClubGridProps) => {
    return (
        <div className="mx-24 mt-12">
            {clubs.length > 0 ? (
                <div className="grid grid-cols-1 m:grid-cols-2 lg:grid-cols-2 xl:grid-cols-5 gap-6">
                    {clubs.map((dto) => {
                        return <ClubSearchCard key={dto.name} club={dto} />;
                    })}
                </div>
            ) : (
                <h2 className="font-bold font-dmSans text-[60px] text-center max-w-7xl pt-6">
                    No results. Are you making places up?
                </h2>
            )}
        </div>
    );
};

export default ClubGrid;
