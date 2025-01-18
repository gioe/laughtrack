import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { SocialData } from "@/objects/class/socialData/SocialData";
import { Phone, Globe, Clock } from "lucide-react";

interface ClubDataColumnProps {
    club: ClubDTO;
}

const ClubDataColumn = ({ club }: ClubDataColumnProps) => {
    const parsedClub = new Club(club);
    return (
        <div className="max-w-2xl bg-cream-50">
            <section>
                <h2 className="text-xl font-bold mb-4">Contact</h2>
                <div className="space-y-3">
                    {parsedClub.phoneNumber !== "" && (
                        <a
                            href={`tel:${parsedClub.phoneNumber}`}
                            className="flex items-center gap-2 text-brown-600 hover:text-brown-700"
                        >
                            <Phone className="w-5 h-5" />
                            <span>{parsedClub.phoneNumber}</span>
                        </a>
                    )}
                    <a
                        href={parsedClub.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-brown-600 hover:text-brown-700"
                    >
                        <Globe className="w-5 h-5" />
                        <span>{parsedClub.website}</span>
                    </a>
                </div>
            </section>
        </div>
    );
};

export default ClubDataColumn;
