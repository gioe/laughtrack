import Link from "next/link";
import Image from "next/image";
import { MapPin } from "lucide-react";
import { RoomHistoryDTO } from "@/objects/class/comedian/roomHistory.interface";

interface RoomHistorySectionProps {
    comedianName: string;
    rooms: RoomHistoryDTO[];
}

const MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
];

function formatLastPlayed(date: Date): string {
    return `${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

function formatPlayCount(count: number): string {
    return `${count.toLocaleString()} ${count === 1 ? "time" : "times"}`;
}

const RoomHistorySection = ({
    comedianName,
    rooms,
}: RoomHistorySectionProps) => {
    if (rooms.length === 0) return null;

    return (
        <section
            aria-label={`Venues ${comedianName} has performed at`}
            className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 pt-8 pb-2"
        >
            <header className="mb-4">
                <h2 className="font-gilroy-bold text-h2 font-bold text-foreground">
                    Where {comedianName} performs
                </h2>
                <p className="text-gray-600 font-dmSans text-body">
                    Counts of past sets across every venue with show history.
                </p>
            </header>

            <ul
                role="list"
                className="flex gap-4 overflow-x-auto pb-3 md:grid md:grid-cols-2 lg:grid-cols-3 md:overflow-x-visible md:pb-0"
            >
                {rooms.map((room) => (
                    <li key={room.clubId} className="flex">
                        <RoomTile room={room} />
                    </li>
                ))}
            </ul>
        </section>
    );
};

const RoomTile = ({ room }: { room: RoomHistoryDTO }) => {
    const locationLabel =
        room.clubCity && room.clubState
            ? `${room.clubCity}, ${room.clubState}`
            : (room.clubCity ?? room.clubState ?? null);

    return (
        <Link
            href={`/club/${room.clubName}`}
            data-testid={`room-history-tile-${room.clubId}`}
            className="flex-shrink-0 w-64 md:w-auto flex-1 bg-gradient-to-b from-white to-coconut-cream/60 rounded-xl overflow-hidden shadow-sm border-b-2 border-transparent transition-all duration-300 hover:shadow-lg hover:border-copper"
        >
            <div className="relative w-full aspect-video bg-coconut-cream/40">
                <Image
                    src={room.imageUrl}
                    alt=""
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 256px, (max-width: 1024px) 50vw, 33vw"
                />
            </div>
            <div className="p-3 space-y-1">
                <h3 className="font-bold text-foreground text-sm line-clamp-1">
                    {room.clubName}
                </h3>
                <p className="text-xs text-gray-700 font-dmSans">
                    Played {formatPlayCount(room.playCount)} · last set{" "}
                    {formatLastPlayed(room.lastPlayedDate)}
                </p>
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

export default RoomHistorySection;
