import { Club } from "@/objects/class/club/Club";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { Phone, Globe, MapPin, Clock } from "lucide-react";

interface ClubDataColumnProps {
    club: ClubDTO;
}

const DAY_ORDER = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
];

function orderHoursEntries(hours: Record<string, string>): [string, string][] {
    const entries = Object.entries(hours);
    return entries.sort(([a], [b]) => {
        const ai = DAY_ORDER.indexOf(a.toLowerCase());
        const bi = DAY_ORDER.indexOf(b.toLowerCase());
        if (ai === -1 && bi === -1) return 0;
        if (ai === -1) return 1;
        if (bi === -1) return -1;
        return ai - bi;
    });
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
    const hoursEntries = parsedClub.hours
        ? orderHoursEntries(parsedClub.hours)
        : [];

    const hasContact =
        parsedClub.phoneNumber !== "" || parsedClub.website !== "" || mapUrl;

    return (
        <div className="max-w-2xl bg-coconut-cream space-y-6">
            {parsedClub.description !== "" && (
                <section>
                    <h2 className="text-xl font-bold mb-2">
                        {isFestival ? "About the Festival" : "About"}
                    </h2>
                    <p className="text-cedar whitespace-pre-line">
                        {parsedClub.description}
                    </p>
                </section>
            )}
            {hoursEntries.length > 0 && (
                <section>
                    <h2 className="text-xl font-bold mb-2 flex items-center gap-2">
                        <Clock className="w-5 h-5" aria-hidden="true" />
                        Hours
                    </h2>
                    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-cedar">
                        {hoursEntries.map(([day, hours]) => (
                            <div key={day} className="contents">
                                <dt className="capitalize font-medium">
                                    {day}
                                </dt>
                                <dd>{hours}</dd>
                            </div>
                        ))}
                    </dl>
                </section>
            )}
            {hasContact && (
                <section>
                    <h2 className="text-xl font-bold mb-4">
                        {isFestival ? "Festival Info" : "Contact"}
                    </h2>
                    <div className="space-y-3">
                        {parsedClub.phoneNumber !== "" && (
                            <a
                                href={`tel:${parsedClub.phoneNumber}`}
                                className="flex items-center gap-2 text-cedar hover:text-paarl"
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
                                className="flex items-center gap-2 text-cedar hover:text-paarl"
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
                                className="flex items-center gap-2 text-cedar hover:text-paarl"
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
