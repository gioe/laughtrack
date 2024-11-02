import { ClubInterface, Filter } from "../../../interfaces";

export const filterClubs = (
    clubs: ClubInterface[],
    filter: Filter,
): ClubInterface[] => {
    return clubs.filter((club: ClubInterface) => {
        return true;
    });
};
