import { ClubInterface } from "../../../interfaces";

export const sortClubs = (
    clubs: ClubInterface[],
    sortValue?: string,
): ClubInterface[] => {
    return clubs.sort((a: ClubInterface, b: ClubInterface) => {
        if (sortValue == "alphabetical") return a.name < b.name ? -1 : 1;
        else
            return (
                (b.socialData.popularityScore ?? 0) -
                (a.socialData.popularityScore ?? 0)
            );
    });
};
