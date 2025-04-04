import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import InstagramIcon from "@/ui/components/icons/InstagramIcon";
import TikTokIcon from "@/ui/components/icons/TikTokIcon";
import YouTubeIcon from "@/ui/components/icons/YouTubeIcon";
import { Globe, ExternalLink } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

interface SocialMediaColumnProps {
    comedian: ComedianDTO;
}

const SocialMediaColumn = ({ comedian }: SocialMediaColumnProps) => {
    const parsedComedian = new Comedian(comedian);
    const [hoveredLink, setHoveredLink] = useState<string | null>(null);

    const socialLinks = [
        {
            platform: "Instagram",
            account: parsedComedian.socialData?.instagram.account,
            url: `https://instagram.com/${parsedComedian.socialData?.instagram.account}`,
            icon: InstagramIcon,
        },
        {
            platform: "TikTok",
            account: parsedComedian.socialData?.tiktok.account,
            url: `https://tiktok.com/${parsedComedian.socialData?.tiktok.account}`,
            icon: TikTokIcon,
        },
        {
            platform: "YouTube",
            account: parsedComedian.socialData?.youtube.account,
            url: `https://youtube.com/${parsedComedian.socialData?.youtube.account}`,
            icon: YouTubeIcon,
        },
        {
            platform: "Website",
            account: parsedComedian.socialData?.website,
            url: `https://${parsedComedian.socialData?.website}`,
            icon: Globe,
        },
    ];

    return (
        <div className="bg-white/50 rounded-xl p-6 shadow-sm">
            <motion.h2
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="text-xl font-bold mb-6 text-gray-900"
            >
                Social Media
            </motion.h2>

            <div className="space-y-4">
                {socialLinks.map((link, index) => {
                    if (!link.account) return null;
                    const Icon = link.icon;

                    return (
                        <motion.a
                            key={link.platform}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.3, delay: index * 0.1 }}
                            onMouseEnter={() => setHoveredLink(link.platform)}
                            onMouseLeave={() => setHoveredLink(null)}
                            className={`flex items-center justify-between p-3 rounded-lg transition-all duration-200 ${
                                hoveredLink === link.platform
                                    ? "bg-gray-50 shadow-sm"
                                    : "hover:bg-gray-50"
                            }`}
                        >
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-gray-100 rounded-lg">
                                    <Icon className="w-5 h-5 text-gray-700" />
                                </div>
                                <div>
                                    <div className="font-medium text-gray-900">
                                        {link.platform}
                                    </div>
                                    <div className="text-sm text-gray-500">
                                        {link.account}
                                    </div>
                                </div>
                            </div>
                            <ExternalLink className="w-4 h-4 text-gray-400" />
                        </motion.a>
                    );
                })}
            </div>
        </div>
    );
};

export default SocialMediaColumn;
