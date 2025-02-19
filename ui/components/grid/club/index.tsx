"use server";

import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubSearchCard from "../../cards/club/search";

interface ClubGridProps {
    clubs: ClubDTO[];
}
const ClubGrid = ({ clubs }: ClubGridProps) => {
    return (
        <div className="md:mx-10 lg:mx-10 mt-12">
            {clubs.length > 0 ? (
                <div className="grid grid-cols-2 gap-6 m:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                    {clubs.map((dto) => {
                        return <ClubSearchCard key={dto.name} club={dto} />;
                    })}
                </div>
            ) : (
                <h2 className="font-bold font-dmSans text-[60px] text-center pt-6">
                    No results. Does that place even exist?
                </h2>
            )}
        </div>
    );
};

export default ClubGrid;
