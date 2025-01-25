"use server";

import { ClubDTO } from "@/objects/class/club/club.interface";
import ClubSearchCard from "../../cards/club/search";

interface ClubGridProps {
    clubs: ClubDTO[];
}
const ClubGrid = ({ clubs }: ClubGridProps) => {
    return (
        <div className="mx-24 my-12">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {clubs.map((dto) => {
                    return <ClubSearchCard key={dto.name} club={dto} />;
                })}
            </div>
        </div>
    );
};

export default ClubGrid;
