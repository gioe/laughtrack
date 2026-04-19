"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianHeadshot from "../../image/comedian";
import EntityCard from "../entity";

interface ComedianGridCardProps {
    entity: ComedianDTO;
    isTrending?: boolean;
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({
    entity,
    isTrending,
}) => {
    const comedian = new Comedian(entity);
    return (
        <EntityCard
            chrome="none"
            className="relative h-full flex flex-col items-center"
        >
            <ComedianHeadshot
                comedian={comedian}
                sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                variant="grid"
            />

            <div className="mt-4 space-y-2 w-full">
                <h3 className="text-h3 font-extrabold font-gilroy-bold text-center text-cedar hover:text-[#2D1810] transition-colors">
                    {comedian.name}
                </h3>

                {isTrending && (
                    <div className="flex justify-center">
                        <span
                            className="w-2 h-2 rounded-full bg-copper"
                            aria-hidden="true"
                        />
                    </div>
                )}

                <div className="flex justify-center">
                    <span className="bg-copper/10 text-copper text-xs px-2 py-0.5 rounded-full font-dmSans">
                        {comedian.coAppearances
                            ? `Performed together ${comedian.coAppearances} times`
                            : `${comedian.showCount ?? 0} upcoming shows`}
                    </span>
                </div>
            </div>
        </EntityCard>
    );
};

export default ComedianGridCard;
