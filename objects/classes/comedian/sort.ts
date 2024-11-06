import { SortProperty } from "../../../util/enum";
import { Comedian } from "./Comedian";

export const sortComedians = (
    comedians: Comedian[],
    sortValue?: SortProperty,
): Comedian[] => {
    return comedians.sort((a: Comedian, b: Comedian) => {
        switch (sortValue) {
            case SortProperty.Alphabetical: return a.name < b.name ? -1 : 1;
            default:
                return (
                    (b.socialData.popularityScore ?? 0) -
                    (a.socialData.popularityScore ?? 0)
                );
        }
    });
};
