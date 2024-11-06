import { SortProperty } from "../../../util/enum";
import { Club } from "./Club";

export const sortClubs = (
    clubs: Club[],
    sortValue: SortProperty,
): Club[] => {
    return clubs.sort((a: Club, b: Club) => {
        switch (sortValue) {
            case SortProperty.Alphabetical: return a.name < b.name ? -1 : 1;
            default: return (
                (b.socialData.popularityScore ?? 0) -
                (a.socialData.popularityScore ?? 0)
            );
        }
    });
};
