import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Phone, Globe } from "lucide-react";

interface ClubDataColumnProps {
    club: ClubDTO;
}

const ClubDataColumn = ({ club }: ClubDataColumnProps) => {
    const parsedClub = new Club(club);
    return (
        <div className="max-w-2xl bg-coconut-cream">
            <section>
                <h2 className="text-xl font-bold mb-4">Contact</h2>
                <div className="space-y-3">
                    {parsedClub.phoneNumber !== "" && (
                        <a
                            href={`tel:${parsedClub.phoneNumber}`}
                            className="flex items-center gap-2 text-cedar hover:text-copper"
                        >
                            <Phone className="w-5 h-5" />
                            <span>{parsedClub.phoneNumber}</span>
                        </a>
                    )}
                    <a
                        href={parsedClub.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-cedar hover:text-copper"
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
