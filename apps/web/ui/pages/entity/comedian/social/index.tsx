"use client";

import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import InstagramIcon from "@/ui/components/icons/InstagramIcon";
import TikTokIcon from "@/ui/components/icons/TikTokIcon";
import YouTubeIcon from "@/ui/components/icons/YouTubeIcon";
import { Globe, ExternalLink, Share2 } from "lucide-react";
import { motion } from "framer-motion";
import { useMotionProps } from "@/hooks";
import { useState } from "react";
import toast from "react-hot-toast";

interface SocialMediaColumnProps {
    comedian: ComedianDTO;
}

const SocialMediaColumn = ({ comedian }: SocialMediaColumnProps) => {
    const { mv, mp } = useMotionProps();
    const parsedComedian = new Comedian(comedian);
    const [hoveredLink, setHoveredLink] = useState<string | null>(null);
    const [copiedPlatform, setCopiedPlatform] = useState<string | null>(null);

    const socialLinks = [
        {
            platform: "Instagram",
            account: parsedComedian.socialData?.instagram.account,
            url: `https://instagram.com/${parsedComedian.socialData?.instagram.account}`,
            icon: InstagramIcon,
            color: "hover:text-[#CD6837]",
            bgColor: "hover:bg-[#CD6837]/10",
        },
        {
            platform: "TikTok",
            account: parsedComedian.socialData?.tiktok.account,
            url: `https://tiktok.com/${parsedComedian.socialData?.tiktok.account}`,
            icon: TikTokIcon,
            color: "hover:text-black",
            bgColor: "hover:bg-black/10",
        },
        {
            platform: "YouTube",
            account: parsedComedian.socialData?.youtube.account,
            url: `https://youtube.com/${parsedComedian.socialData?.youtube.account}`,
            icon: YouTubeIcon,
            color: "hover:text-red-600",
            bgColor: "hover:bg-red-600/10",
        },
        {
            platform: "Website",
            account: parsedComedian.socialData?.website,
            url: `https://${parsedComedian.socialData?.website}`,
            icon: Globe,
            color: "hover:text-blue-600",
            bgColor: "hover:bg-blue-600/10",
        },
    ];

    const handleShare = async (
        link: (typeof socialLinks)[0],
        e: React.MouseEvent,
    ) => {
        e.preventDefault();
        e.stopPropagation();

        try {
            await navigator.clipboard.writeText(link.url);
            setCopiedPlatform(link.platform);
            toast.success(`${link.platform} link copied to clipboard!`);
            setTimeout(() => setCopiedPlatform(null), 2000);
        } catch {
            toast.error("Failed to copy link");
        }
    };

    return (
        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-sm border border-gray-100">
            <motion.h2
                initial={{ opacity: 0, y: mv(20) }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: mv(0.3) }}
                className="text-2xl font-bold mb-6 text-gray-900 font-dmSans"
            >
                Connect
            </motion.h2>

            <div className="space-y-3">
                {socialLinks.map((link, index) => {
                    if (!link.account) return null;
                    const Icon = link.icon;
                    const isHovered = hoveredLink === link.platform;
                    const isCopied = copiedPlatform === link.platform;

                    return (
                        <motion.div
                            key={link.platform}
                            initial={{ opacity: 0, x: mv(-20) }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{
                                duration: mv(0.3),
                                delay: mv(index * 0.1),
                            }}
                            className="relative"
                        >
                            <motion.a
                                href={link.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onMouseEnter={() =>
                                    setHoveredLink(link.platform)
                                }
                                onMouseLeave={() => setHoveredLink(null)}
                                className={`flex items-center justify-between p-4 rounded-lg transition-all duration-200 group ${
                                    isHovered
                                        ? `${link.bgColor} shadow-sm`
                                        : "hover:bg-gray-50"
                                }`}
                            >
                                <div className="flex items-center gap-3">
                                    <motion.div
                                        className={`p-2 rounded-lg transition-colors ${
                                            isHovered
                                                ? "bg-white"
                                                : "bg-gray-100"
                                        }`}
                                        whileHover={mp({ scale: 1.05 })}
                                        whileTap={mp({ scale: 0.95 })}
                                    >
                                        <Icon
                                            className={`w-5 h-5 transition-colors ${link.color}`}
                                        />
                                    </motion.div>
                                    <div>
                                        <div
                                            className={`font-medium transition-colors ${link.color} font-dmSans`}
                                        >
                                            {link.platform}
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            {link.account}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <motion.button
                                        onClick={(e) => handleShare(link, e)}
                                        whileHover={mp({ scale: 1.1 })}
                                        whileTap={mp({ scale: 0.9 })}
                                        className={`p-2 rounded-full transition-colors ${
                                            isHovered
                                                ? "bg-white"
                                                : "bg-transparent"
                                        }`}
                                    >
                                        <Share2
                                            className={`w-4 h-4 ${
                                                isCopied
                                                    ? "text-green-500"
                                                    : "text-gray-400"
                                            }`}
                                        />
                                    </motion.button>
                                    <motion.div
                                        whileHover={mp({ scale: 1.1 })}
                                        whileTap={mp({ scale: 0.9 })}
                                        className={`p-2 rounded-full transition-colors ${
                                            isHovered
                                                ? "bg-white"
                                                : "bg-transparent"
                                        }`}
                                    >
                                        <ExternalLink
                                            className={`w-4 h-4 ${link.color}`}
                                        />
                                    </motion.div>
                                </div>
                            </motion.a>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
};

export default SocialMediaColumn;
