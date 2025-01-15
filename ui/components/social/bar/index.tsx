"use client";

import { SocialData } from "@/objects/class/socialData/SocialData";
import { Tooltip } from "@material-tailwind/react";
import WebIcon from "../../icons/WebIcon";
import TikTokIcon from "../../icons/TikTokIcon";
import InstagramIcon from "../../icons/InstagramIcon";
import YouTubeIcon from "../../icons/YouTubeIcon";

interface SocialMediaBarProps {
    data: SocialData;
    className?: string;
}

interface SocialLink {
    platform: string;
    account: string | null;
    url: string;
    Icon: React.FC;
}

const SocialMediaBar: React.FC<SocialMediaBarProps> = ({
    data,
    className = "",
}) => {
    const baseClasses = `cursor-pointer rounded-full p-3 text-gray-900 transition-colors inline-flex items-center`;

    const socialLinks: SocialLink[] = [
        {
            platform: "Instagram",
            account: data.instagram.account,
            url: `https://instagram.com/${data.instagram.account}`,
            Icon: InstagramIcon,
        },
        {
            platform: "TikTok",
            account: data.tiktok.account,
            url: `https://tiktok.com/@${data.tiktok.account}`,
            Icon: TikTokIcon,
        },
        {
            platform: "YouTube",
            account: data.youtube.account,
            url: `https://www.youtube.com/@${data.youtube.account}`,
            Icon: YouTubeIcon,
        },
    ];

    const handleClick = (url: string, e: React.MouseEvent) => {
        e.preventDefault();
        // Open in new tab with security best practices
        window.open(url, "_blank", "noopener,noreferrer");
    };

    const renderSocialIcon = ({ platform, account, url, Icon }: SocialLink) => {
        if (!account) return null;

        return (
            <Tooltip key={platform} content={account}>
                <a
                    href={url}
                    onClick={(e) => handleClick(url, e)}
                    aria-label={`Visit ${platform} profile`}
                >
                    <Icon />
                </a>
            </Tooltip>
        );
    };

    return (
        <div
            className={`flex gap-4 justify-center items-center h-6 ${className}`}
        >
            {socialLinks.map((link) => renderSocialIcon(link))}

            {data.website && (
                <Tooltip content={data.website}>
                    <a
                        href={data.website}
                        onClick={(e) => handleClick(data.website, e)}
                        aria-label="Visit website"
                    >
                        <WebIcon />
                    </a>
                </Tooltip>
            )}
        </div>
    );
};

export default SocialMediaBar;
