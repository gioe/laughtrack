import type { ShowDTO } from "@/objects/class/show/show.interface";
import ShowTable from "@/ui/pages/search/table";

interface ClubShowRoomsProps {
    shows: ShowDTO[];
}

interface RoomGroup {
    room: string | null;
    shows: ShowDTO[];
}

export function normalizedRoom(room: string | null | undefined) {
    const value = room?.trim();
    return value ? value : null;
}

export function groupShowsByRoom(shows: ShowDTO[]): RoomGroup[] {
    const groups: RoomGroup[] = [];
    const groupIndexes = new Map<string, number>();

    shows.forEach((show) => {
        const room = normalizedRoom(show.room);
        const key = room ?? "";
        const existingIndex = groupIndexes.get(key);

        if (existingIndex == null) {
            groupIndexes.set(key, groups.length);
            groups.push({ room, shows: [show] });
            return;
        }

        groups[existingIndex].shows.push(show);
    });

    return groups;
}

export function hasMultipleRooms(shows: ShowDTO[]) {
    const rooms = new Set(
        shows.flatMap((show) => {
            const room = normalizedRoom(show.room);
            return room ? [room] : [];
        }),
    );

    return rooms.size > 1;
}

export default function ClubShowRooms({ shows }: ClubShowRoomsProps) {
    if (!hasMultipleRooms(shows)) {
        return <ShowTable shows={shows} hideClubName />;
    }

    const roomGroups = groupShowsByRoom(shows);

    return (
        <section
            className="px-4 sm:px-6 md:px-8 mb-10 space-y-10"
            aria-label="Upcoming shows by room"
        >
            {roomGroups.map((group) => (
                <div
                    key={group.room ?? "unassigned-room"}
                    className="space-y-4"
                >
                    <h2 className="font-gilroy-bold text-2xl font-bold text-foreground">
                        {group.room ?? "Other shows"}
                    </h2>
                    <ShowTable shows={group.shows} hideClubName />
                </div>
            ))}
        </section>
    );
}
