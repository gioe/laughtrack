"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import { useMotionProps } from "@/hooks";

export default function AuthImageContent() {
    const { mv } = useMotionProps();

    return (
        <div className="invisible lg:visible lg:w-1/2 lg:relative lg:bg-gray-900 overflow-hidden">
            <motion.div
                initial={{ scale: mv(1.1, 1), opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{
                    duration: mv(1.2),
                    ease: "easeOut",
                }}
                className="relative w-full h-full"
            >
                <Image
                    src="/sidebar.png"
                    alt="Comedy show"
                    className="object-cover"
                    fill
                    priority
                    quality={90}
                />
                <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/40 to-black/60" />
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: mv(20) }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                    duration: mv(0.8),
                    delay: mv(0.4),
                }}
                className="absolute inset-0 flex flex-col justify-end p-12"
            >
                <div className="max-w-lg mx-auto text-center text-white">
                    <motion.h2
                        initial={{ opacity: 0, y: mv(20) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{
                            duration: mv(0.6),
                            delay: mv(0.6),
                        }}
                        className="text-4xl font-bold mb-6 font-chivo"
                    >
                        Laugh Local
                    </motion.h2>

                    <motion.p
                        initial={{ opacity: 0, y: mv(20) }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{
                            duration: mv(0.6),
                            delay: mv(0.8),
                        }}
                        className="text-lg opacity-90 font-dmSans leading-relaxed"
                    >
                        Laughtrack wants to get you out of the house. Find funny
                        shows. Follow funny comedians. Get informed when funny
                        comedians put on funny shows. Turn off that podcast and
                        go see the real thing.
                    </motion.p>
                </div>
            </motion.div>
        </div>
    );
}
