"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import SocialMediaBar from "../../social/bar";
import ComedianHeadshot from "../../image/comedian";

interface ComedianGridCardProps {
    entity: string;
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({ entity }) => {
    const comedian = new Comedian(JSON.parse(entity) as ComedianDTO);
    return (
        <div className="bg-coconut-cream rounded-xl overflow-hidden pb-4 px-4">
            <ComedianHeadshot
                comedian={comedian}
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                variant="grid"
            />

            <div className="mt-4">
                <h2 className="text-[22px] font-bold mb-1  font-gilroy-bold text-center">
                    {comedian.name}
                </h2>

                <p className="text-[18px] text-gray-600 mb-4 text-center font-dmSans">
                    {`${comedian.showCount ?? 0} upcoming shows`}
                </p>

                <div className="w-full">
                    {comedian.socialData && (
                        <SocialMediaBar data={comedian.socialData} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default ComedianGridCard;
