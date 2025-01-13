import { SocialData } from "@/objects/class/socialData/SocialData";

interface SocialMediaColumnProps {
    socialData?: SocialData;
}

const SocialMediaColumn = ({ socialData }: SocialMediaColumnProps) => {
    return (
        <div className="w-64">
            <h2 className="text-xl font-bold mb-4">Social Media</h2>
            <div className="space-y-2">
                {socialData?.instagram.account && (
                    <a
                        href="#"
                        className="text-brown-600 hover:underline block"
                    >
                        {`instagram.com/${socialData.instagram.account}`}
                    </a>
                )}

                {socialData?.tiktok.account && (
                    <a
                        href="#"
                        className="text-brown-600 hover:underline block"
                    >
                        {`tiktok.com/${socialData.tiktok.account}`}
                    </a>
                )}

                {socialData?.youtube.account && (
                    <a
                        href="#"
                        className="text-brown-600 hover:underline block"
                    >
                        {`youtube.com/${socialData.youtube.account}`}
                    </a>
                )}

                {socialData?.website && (
                    <a
                        href="#"
                        className="text-brown-600 hover:underline block"
                    >
                        {`${socialData.website}`}
                    </a>
                )}
            </div>
        </div>
    );
};

export default SocialMediaColumn;
