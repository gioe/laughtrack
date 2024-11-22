"use client";

import Link from "next/link";
import InstagramIcon from "../icons/InstagramIcon";
import TikTokIcon from "../icons/TikTokIcon";
import WebIcon from "../icons/WebIcon";
import YouTubeIcon from "../icons/YoutubeIcon";
import { SocialData } from "../../objects/class/socialData/SocialData";
interface SocialMediaBarProps {
    data: SocialData;
}

const SocialMediaBar: React.FC<SocialMediaBarProps> = ({ data }) => {
    const hasInstagram = data.instagram.account !== null;
    const hasTikTok = data.tiktok.account !== null;
    const hasYouTube = data.youtube.account !== null;
    return (
        <div className="flex flex-row gap-4 justify-center items-center pb-6">
            {hasInstagram && (
                <Link href={`https://instagram.com/${data.instagram.account}`}>
                    <InstagramIcon className="instagram-icon" />
                </Link>
            )}

            {hasTikTok && (
                <Link href={`https://tiktok.com/@${data.tiktok.account}`}>
                    <TikTokIcon className="tiktok-icon" />
                </Link>
            )}

            {hasYouTube && (
                <Link href={`https://www.youtube.com/@${data.youtube.account}`}>
                    <YouTubeIcon className="youtube-icon" />
                </Link>
            )}

            {data.website && (
                <Link href={data.website}>
                    <WebIcon className="web-icon" />
                </Link>
            )}
        </div>
    );
};

export default SocialMediaBar;
