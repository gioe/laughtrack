import { Club } from "./Club";

export const filterClubs = (
    clubs: Club[],
): Club[] => {
    return clubs.filter((club: Club) => {
        return club;
    });
};
