"use client";

import Link from "next/link";
import InstagramIcon from "../icons/InstagramIcon";
import TikTokIcon from "../icons/TikTokIcon";
import WebIcon from "../icons/WebIcon";
import YouTubeIcon from "../icons/YoutubeIcon";
import { SocialDataInterface } from "../../objects/interface";

interface SocialMediaBarProps {
    data: SocialDataInterface;
}

const SocialMediaBar: React.FC<SocialMediaBarProps> = ({ data }) => {
    return (
        <div className="flex flex-row gap-4 justify-center items-center pb-6">
            {data.instagram && (
                <Link href={`https://instagram.com/${data.instagram.account}`}>
                    <InstagramIcon className="instagram-icon" />
                </Link>
            )}

            {data.tiktok && (
                <Link href={`https://tiktok.com/@${data.tiktok.account}`}>
                    <TikTokIcon className="tiktok-icon" />
                </Link>
            )}

            {data.youtube && (
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
