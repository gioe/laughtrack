"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianHeadshot from "../../image/comedian";
import EntityCard from "../entity";

interface ComedianGridCardProps {
    entity: ComedianDTO;
    isTrending?: boolean;
    variant?: "default" | "compact";
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({
    entity,
    isTrending,
    variant = "default",
}) => {
    const comedian = new Comedian(entity);
    const isCompact = variant === "compact";

    return (
        <EntityCard
            chrome="none"
            className={`relative h-full flex flex-col ${
                isCompact ? "items-start" : "items-center"
            }`}
        >
            <ComedianHeadshot
                comedian={comedian}
                className={
                    isCompact ? "w-20 sm:w-24 md:w-28 lg:w-full max-w-28" : ""
                }
                sizes={
                    isCompact
                        ? "(max-width: 640px) 80px, (max-width: 768px) 96px, 112px"
                        : "(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                }
                variant={isCompact ? "compactGrid" : "grid"}
            />

            <div
                className={`w-full ${
                    isCompact ? "mt-3 space-y-1.5" : "mt-4 space-y-2"
                }`}
            >
                <h3
                    className={`font-extrabold font-gilroy-bold text-cedar hover:text-cedar-dark transition-colors ${
                        isCompact
                            ? "text-base leading-tight text-left"
                            : "text-h3 text-center"
                    }`}
                >
                    {comedian.name}
                </h3>

                {isTrending && (
                    <div className={isCompact ? "flex" : "flex justify-center"}>
                        <span
                            className="w-2 h-2 rounded-full bg-copper"
                            aria-hidden="true"
                        />
                    </div>
                )}

                <div className={isCompact ? "flex" : "flex justify-center"}>
                    <span className="bg-copper/10 text-copper text-xs px-2 py-0.5 rounded-full font-dmSans leading-tight">
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
