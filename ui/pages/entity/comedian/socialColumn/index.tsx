import { SocialData } from "@/objects/class/socialData/SocialData";

interface SocialMediaColumnProps {
    socialData?: SocialData;
}

const SocialMediaColumn = ({ socialData }: SocialMediaColumnProps) => (
    <div className="w-64">
        <h2 className="text-xl font-bold mb-4">Social Media</h2>
        <div className="space-y-2">
            <a href="#" className="text-brown-600 hover:underline block">
                instagram.com/rubysimmons
            </a>
            <a href="#" className="text-brown-600 hover:underline block">
                tiktok.com/rubysimms
            </a>
            <a href="#" className="text-brown-600 hover:underline block">
                youtube.com/rubysimmons
            </a>
        </div>
    </div>
);

export default SocialMediaColumn;
