import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Phone, Globe, MapPin } from "lucide-react";

interface ClubDataColumnProps {
    club: ClubDTO;
}

function buildMapQuery(parsedClub: Club): string | null {
    const parts = [
        parsedClub.name,
        parsedClub.address,
        parsedClub.city,
        parsedClub.state,
        parsedClub.zipCode,
    ].filter((v) => typeof v === "string" && v.trim() !== "");
    if (parts.length === 0) return null;
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(parts.join(", "))}`;
}

const ClubDataColumn = ({ club }: ClubDataColumnProps) => {
    const parsedClub = new Club(club);
    const isFestival = parsedClub.clubType === "festival";

    const mapUrl = buildMapQuery(parsedClub);

    const hasContact =
        parsedClub.phoneNumber !== "" || parsedClub.website !== "" || mapUrl;

    return (
        <div className="max-w-2xl bg-coconut-cream space-y-6">
            {hasContact && (
                <section>
                    <h2 className="text-xl font-bold mb-4">
                        {isFestival ? "Festival Info" : "Contact"}
                    </h2>
                    <div className="space-y-3">
                        {parsedClub.phoneNumber !== "" && (
                            <a
                                href={`tel:${parsedClub.phoneNumber}`}
                                className="flex items-center gap-2 text-foreground hover:text-paarl"
                            >
                                <Phone className="w-5 h-5" />
                                <span>{parsedClub.phoneNumber}</span>
                            </a>
                        )}
                        {parsedClub.website !== "" && (
                            <a
                                href={parsedClub.website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-foreground hover:text-paarl"
                            >
                                <Globe className="w-5 h-5" />
                                <span>
                                    {isFestival
                                        ? "Visit Festival Website"
                                        : parsedClub.website}
                                </span>
                            </a>
                        )}
                        {mapUrl && (
                            <a
                                href={mapUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-foreground hover:text-paarl"
                            >
                                <MapPin className="w-5 h-5" />
                                <span>View on Google Maps</span>
                            </a>
                        )}
                    </div>
                </section>
            )}
        </div>
    );
};

export default ClubDataColumn;
