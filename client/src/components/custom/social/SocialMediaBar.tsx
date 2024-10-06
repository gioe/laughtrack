'use client';

import Link from "next/link";
import InstagramIcon from "../icons/InstagramIcon";
import TikTokIcon from "../icons/TikTokIcon";
import WebIcon from "../icons/WebIcon";
import { SocialDataInterface } from "@/interfaces/socialData.interface";

interface SocialMediaBarProps {
    data: SocialDataInterface;

}
const SocialMediaBar: React.FC<SocialMediaBarProps> = ({
    data
}) => {
    return (
        <div className="flex flex-row gap-4 justify-center pt-6">

            {data.instagramAccount && (
                <Link
                href={`https://instagram.com/${data.instagramAccount}`}
                >
                    <InstagramIcon className='instagram-icon' />
                </Link>
            )}

            {data.tiktokAccount && (
                <Link
                                href={`https://tiktok.com/@${data.tiktokAccount}`}
                >
                    <TikTokIcon className='tiktok-icon' />
                </Link>
            )}

            {data.website && (
                                <Link
                                href={data.website}
                            >
                <WebIcon className='web-icon' />
                </Link>
            )}

        </div>
    )
}

export default SocialMediaBar;