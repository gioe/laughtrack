
import { EntityType } from "../enum";
import * as hooks from "../../hooks";

export const getMenuItemsForEntityType = (type: EntityType) => {
    switch (type) {
        case EntityType.Club:
            return MENU_OPTIONS.CLUB
        case EntityType.Show:
            return MENU_OPTIONS.SHOW
        case EntityType.Comedian:
            return MENU_OPTIONS.COMEDIAN
    }
}

const MENU_OPTIONS = {
    COMEDIAN: [
        { key: "social", label: "Edit Social Data", store: hooks.useSocialDataModal },
        { key: "merge", label: "Merge Comedians", store: hooks.useMergeComediansModal },
        { key: "tags", label: "Add Tags", store: hooks.useAddComedianModal },
    ],
    CLUB: [
        { key: "tags", label: "Add Tags", store: hooks.useAddClubTagModal },
        { key: "scrape", label: "Run Scrape", store: hooks.useRunScrapeModal },
        { key: "clear", label: "Clear SHows", store: hooks.useClearShowsModal },
    ],
    SHOW: [
        { key: "tags", label: "Add Tags", store: hooks.useAddShowTagModal },
        { key: "comedian", label: "Add Comedian", store: hooks.useAddComedianModal },
    ],
};
