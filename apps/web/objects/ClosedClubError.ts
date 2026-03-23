export class ClosedClubError extends Error {
    clubName: string;
    closedAt: Date | null;

    constructor(clubName: string, closedAt: Date | null) {
        super(`Club "${clubName}" has permanently closed`);
        this.name = "ClosedClubError";
        this.clubName = clubName;
        this.closedAt = closedAt;
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
