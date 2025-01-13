"use server";

import { ClubDTO } from "@/objects/class/club/club.interface";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianCarouselCard from "@/ui/components/grid/comedian/card";
import Link from "next/link";
import ClubCarouselCard from "./card";
import { Club } from "@/objects/class/club/Club";

interface ClubGridProps {
    contentString: string;
}
const ClubGrid = ({ contentString }: ClubGridProps) => {
    const clubs = JSON.parse(contentString) as ClubDTO[];
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 lg:grid-rows-2">
            {clubs.map((dto) => {
                const club = new Club(dto);
                return (
                    <ClubCarouselCard
                        key={dto.name}
                        entity={JSON.stringify(club)}
                    />
                );
            })}
        </div>
    );
};

export default ClubGrid;
