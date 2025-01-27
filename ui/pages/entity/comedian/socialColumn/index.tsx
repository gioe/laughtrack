import { Comedian } from "@/objects/class/comedian/Comedian";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

interface SocialMediaColumnProps {
    comedian: ComedianDTO;
}

const SocialMediaColumn = ({ comedian }: SocialMediaColumnProps) => {
    const parsedComedian = new Comedian(comedian);
    const className =
        "text-copper text-[16px] font-dmSans hover:underline block";

    return (
        <div className="w-64">
            <div className="space-y-2">
                {parsedComedian.socialData?.instagram.account && (
                    <a
                        href={`instagram.com/${parsedComedian.socialData.instagram.account}`}
                        className={className}
                    >
                        {`instagram.com/${parsedComedian.socialData.instagram.account}`}
                    </a>
                )}

                {parsedComedian.socialData?.tiktok.account && (
                    <a
                        href={`tiktok.com/${parsedComedian.socialData.tiktok.account}`}
                        className={className}
                    >
                        {`tiktok.com/${parsedComedian.socialData.tiktok.account}`}
                    </a>
                )}

                {parsedComedian.socialData?.youtube.account && (
                    <a
                        href={`youtube.com/${parsedComedian.socialData.youtube.account}`}
                        className={className}
                    >
                        {`youtube.com/${parsedComedian.socialData.youtube.account}`}
                    </a>
                )}

                {parsedComedian.socialData?.website && (
                    <a
                        href={`${parsedComedian.socialData.website}`}
                        className={className}
                    >
                        {`${parsedComedian.socialData.website}`}
                    </a>
                )}
            </div>
        </div>
    );
};

export default SocialMediaColumn;
