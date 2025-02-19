import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import InstagramIcon from "@/ui/components/icons/InstagramIcon";
import TikTokIcon from "@/ui/components/icons/TikTokIcon";
import YouTubeIcon from "@/ui/components/icons/YoutubeIcon";
import { Globe } from "lucide-react";

interface SocialMediaColumnProps {
    comedian: ComedianDTO;
}

const SocialMediaColumn = ({ comedian }: SocialMediaColumnProps) => {
    const parsedComedian = new Comedian(comedian);
    const className =
        "text-copper text-[16px] font-dmSans hover:underline flex items-center gap-2";

    return (
        <div className="w-64">
            <h2 className="text-xl font-bold mb-4">Socials</h2>

            <div className="space-y-2">
                {parsedComedian.socialData?.instagram.account && (
                    <a
                        href={`instagram.com/${parsedComedian.socialData.instagram.account}`}
                        className={className}
                    >
                        <InstagramIcon className="w-5 h-5" />
                        <span>{`${parsedComedian.socialData.instagram.account}`}</span>
                    </a>
                )}

                {parsedComedian.socialData?.tiktok.account && (
                    <a
                        href={`tiktok.com/${parsedComedian.socialData.tiktok.account}`}
                        className={className}
                    >
                        <TikTokIcon className="w-5 h-5" />
                        <span>{`${parsedComedian.socialData.tiktok.account}`}</span>
                    </a>
                )}

                {parsedComedian.socialData?.youtube.account && (
                    <a
                        href={`youtube.com/${parsedComedian.socialData.youtube.account}`}
                        className={className}
                    >
                        <YouTubeIcon className="w-5 h-5" />
                        <span>{`${parsedComedian.socialData.youtube.account}`}</span>
                    </a>
                )}

                {parsedComedian.socialData?.website && (
                    <a
                        href={`${parsedComedian.socialData.website}`}
                        className={className}
                    >
                        <Globe className="w-5 h-5" />
                        <span>{`${parsedComedian.socialData.website}`}</span>
                    </a>
                )}
            </div>
        </div>
    );
};

export default SocialMediaColumn;
