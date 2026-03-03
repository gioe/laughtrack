"use client";

import { ChevronRightIcon } from "@heroicons/react/24/solid";
import { useStyleContext } from "@/contexts/StyleProvider";
import { twMerge } from "tailwind-merge";
import { motion } from "framer-motion";
import Link from "next/link";

interface HeaderItemProps {
    title: string;
    href: string;
    highlighted: boolean;
}

export function SideDrawerItem({ title, href, highlighted }: HeaderItemProps) {
    const baseClasses = `text-[16px] font-semibold font-dmSans 
        w-full group flex items-center justify-between
        rounded-lg py-3 pl-4 pr-3.5 -mx-3
        transition-all duration-200
        hover:bg-copper/5
        ${highlighted ? "text-copper" : "text-gray-700"}`;

    return (
        <motion.div
            whileHover={{ x: 4 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
        >
            <Link href={href} className={twMerge(baseClasses)}>
                <span className="flex items-center gap-2">{title}</span>
                <ChevronRightIcon
                    className={`h-4 w-4 transition-all duration-200 
                        ${highlighted ? "text-copper" : "text-gray-400"}
                        group-hover:text-copper group-hover:translate-x-0.5`}
                />
            </Link>
        </motion.div>
    );
}
