import Link from "next/link";
import Image from "next/image";
import { MapPin } from "lucide-react";
import { SiblingClubDTO } from "@/lib/data/club/detail/findSiblingClubs";

const MAX_VISIBLE = 6;

interface SiblingLocationsProps {
    chainName: string;
    siblings: SiblingClubDTO[];
}

const SiblingLocations = ({ chainName, siblings }: SiblingLocationsProps) => {
    if (siblings.length === 0) return null;

    const visible = siblings.slice(0, MAX_VISIBLE);
    const remaining = siblings.length - MAX_VISIBLE;

    return (
        <section className="max-w-7xl mx-auto px-6 pb-6">
            <h2 className="text-xl font-bold mb-4">
                Other {chainName} Locations
            </h2>

            {/* Mobile: horizontal scroll / Tablet+: grid */}
            <div className="flex gap-4 overflow-x-auto pb-2 md:grid md:grid-cols-2 lg:grid-cols-3 md:overflow-x-visible md:pb-0">
                {visible.map((club) => (
                    <SiblingCard key={club.name} club={club} />
                ))}
            </div>

            {remaining > 0 && (
                <p className="mt-3 text-sm text-gray-600">
                    + {remaining} more location{remaining > 1 ? "s" : ""}
                </p>
            )}
        </section>
    );
};

const SiblingCard = ({ club }: { club: SiblingClubDTO }) => {
    const locationLabel =
        club.city && club.state
            ? `${club.city}, ${club.state}`
            : (club.city ?? club.state);

    return (
        <Link
            href={`/club/${club.name}`}
            className="flex-shrink-0 w-64 md:w-auto bg-gradient-to-b from-white to-coconut-cream/60 rounded-xl overflow-hidden shadow-sm border-b-2 border-transparent transition-all duration-300 hover:shadow-lg hover:border-copper"
        >
            <div className="relative w-full aspect-video">
                <Image
                    src={club.imageUrl}
                    alt={club.name}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 256px, (max-width: 1024px) 50vw, 33vw"
                />
            </div>
            <div className="p-3 space-y-1">
                <h3 className="font-bold text-cedar text-sm">{club.name}</h3>
                {locationLabel && (
                    <p className="flex items-center gap-1 text-xs text-gray-500">
                        <MapPin size={11} aria-hidden="true" />
                        {locationLabel}
                    </p>
                )}
            </div>
        </Link>
    );
};

export default SiblingLocations;
