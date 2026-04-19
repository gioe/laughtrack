"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import LineupGrid from "@/ui/components/lineup";

interface ShowLineupSectionProps {
    lineup: ComedianLineupDTO[];
}

// Client-side because LineupGrid expects Comedian class instances — constructing
// them here means we never send a class across the server→client boundary.
const ShowLineupSection: React.FC<ShowLineupSectionProps> = ({ lineup }) => {
    const parsed = lineup.map((item) => new Comedian(item));

    return (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 mt-10 mb-10">
            <h2 className="font-gilroy-bold text-[26px] font-bold text-cedar mb-4">
                Lineup
            </h2>
            <LineupGrid lineup={parsed} />
        </section>
    );
};

export default ShowLineupSection;
