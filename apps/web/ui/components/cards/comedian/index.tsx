"use client";

import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import ComedianHeadshot from "../../image/comedian";

interface ComedianGridCardProps {
    entity: ComedianDTO;
}

const ComedianGridCard: React.FC<ComedianGridCardProps> = ({ entity }) => {
    const { mp } = useMotionProps();
    const comedian = new Comedian(entity);
    return (
        <motion.div
            className="bg-coconut-cream rounded-xl pb-4 px-4 h-full transition-shadow duration-300 hover:shadow-lg"
            whileHover={mp({ y: -4, transition: { duration: 0.15 } })}
        >
            <ComedianHeadshot
                comedian={comedian}
                sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                variant="grid"
            />

            <div className="mt-4 space-y-2">
                <h2 className="text-[22px] font-bold font-gilroy-bold text-center text-cedar hover:text-[#2D1810] transition-colors">
                    {comedian.name}
                </h2>

                <p className="text-[16px] text-gray-600 text-center font-dmSans">
                    {`${comedian.showCount ?? 0} upcoming shows`}
                </p>
            </div>
        </motion.div>
    );
};

export default ComedianGridCard;
