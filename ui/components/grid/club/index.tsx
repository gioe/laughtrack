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
                <div className="max-w-7xl">
                    <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                        No results.
                    </h2>
                </div>
            )}
        </div>
    );
};

export default ClubGrid;
