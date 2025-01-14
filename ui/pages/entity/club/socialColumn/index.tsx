import { SocialData } from "@/objects/class/socialData/SocialData";
import { Phone, Globe, Clock } from "lucide-react";

interface ClubDataColumnProps {
    telephoneNumber: string;
    website: string;
}

const ClubDataColumn = ({ telephoneNumber, website }: ClubDataColumnProps) => {
    return (
        <div className="max-w-2xl p-6 bg-cream-50">
            <section>
                <h2 className="text-xl font-bold mb-4">Contact</h2>
                <div className="space-y-3">
                    <a
                        href={`tel:${telephoneNumber}`}
                        className="flex items-center gap-2 text-brown-600 hover:text-brown-700"
                    >
                        <Phone className="w-5 h-5" />
                        <span>{telephoneNumber}</span>
                    </a>

                    <a
                        href={website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-brown-600 hover:text-brown-700"
                    >
                        <Globe className="w-5 h-5" />
                        <span>{website}</span>
                    </a>
                </div>
            </section>
        </div>
    );
};

export default ClubDataColumn;
