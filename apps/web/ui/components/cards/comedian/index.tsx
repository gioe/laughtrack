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
            className="relative bg-gradient-to-b from-white to-coconut-cream/60 rounded-xl pb-4 px-4 h-full shadow-sm border-b-2 border-transparent transition-all duration-300 hover:shadow-lg hover:border-copper"
            whileHover={mp({ y: -4, transition: { duration: 0.15 } })}
        >
            <ComedianHeadshot
                comedian={comedian}
                sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                variant="grid"
            />

            <div className="mt-4 space-y-2">
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

                <p className="text-[16px] text-gray-600 text-center font-dmSans">
                    {`${comedian.showCount ?? 0} upcoming shows`}
                </p>
            </div>
        </motion.div>
    );
};

export default ComedianGridCard;
