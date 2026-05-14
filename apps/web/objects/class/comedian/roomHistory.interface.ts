export interface RoomHistoryDTO {
    clubId: number;
    clubName: string;
    clubCity?: string | null;
    clubState?: string | null;
    imageUrl: string;
    playCount: number;
    lastPlayedDate: Date;
}
