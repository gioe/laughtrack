'use client';

import { SocialDataInterface } from "@/interfaces/socialData.interface";
import { useSession } from "next-auth/react";
import { EditComedianDropdown } from "../dropdown/EditComedianDropdown";
import Link from "next/link";
import InstagramIcon from "../icons/InstagramIcon";
import TikTokIcon from "../icons/TikTokIcon";
import WebIcon from "../icons/WebIcon";
import useSocialDataModal from "@/hooks/useSocialDataModal";
import YouTubeIcon from "../icons/YoutubeIcon";

interface SocialMediaBarProps {
    data?: SocialDataInterface,
    showMenu?: boolean
}

const SocialMediaBar: React.FC<SocialMediaBarProps> = ({
    data,
    showMenu
}) => {
    const socialDataModal = useSocialDataModal();

    const session = useSession();

    const editSocialData = () => {
        socialDataModal.onOpen();
    }

    return (
        <div className="flex flex-row gap-4 justify-center items-center pt-6">

            {data?.instagramAccount && data.instagramAccount !== "" && (
                <Link
                    href={`https://instagram.com/${data.instagramAccount}`}
                >
                    <InstagramIcon className='instagram-icon' />
                </Link>
            )}

            {data?.tiktokAccount && data.tiktokAccount !== "" &&(
                <Link
                    href={`https://tiktok.com/@${data.tiktokAccount}`}
                >
                    <TikTokIcon className='tiktok-icon' />
                </Link>
            )}

            {data?.youtubeAccount && data.youtubeAccount !== ""  &&(
                <Link
                    href={`https://www.youtube.com/@${data.youtubeAccount}`}
                >
                    <YouTubeIcon className='youtube-icon' />
                </Link>
            )}

            {data?.website && data.website !== "" && (
                <Link
                    href={data.website}
                >
                    <WebIcon className='web-icon' />
                </Link>
            )}

            {
                session.data?.user.role == 'admin' && showMenu !== false && <EditComedianDropdown handleEditSocialClick={editSocialData} />
            }

        </div>
    )
}

export default SocialMediaBar;