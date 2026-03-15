"use client";

import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianHeadshot from "../../image/comedian";

interface ComedianGridCardProps {
    entity: ComedianDTO;
    isTrending?: boolean;
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({
    entity,
    isTrending,
}) => {
    const { mp } = useMotionProps();
    const comedian = new Comedian(entity);
    return (
        <motion.div
            className="relative h-full flex flex-col items-center"
            whileHover={mp({ y: -4, transition: { duration: 0.15 } })}
        >
            <ComedianHeadshot
                comedian={comedian}
                sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                variant="grid"
            />

            <div className="mt-4 space-y-2 w-full">
                <h2 className="text-[22px] font-extrabold font-gilroy-bold text-center text-cedar hover:text-[#2D1810] transition-colors">
                    {comedian.name}
                </h2>

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
                        {`${comedian.showCount ?? 0} upcoming shows`}
                    </span>
                </div>
            </div>
        </motion.div>
    );
};

export default ComedianGridCard;
