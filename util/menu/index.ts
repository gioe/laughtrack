
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
        { key: "social", label: "Edit Social Data", hook: hooks.useSocialDataModal },
        { key: "merge", label: "Merge Comedians", hook: hooks.useMergeComediansModal },
        { key: "tags", label: "Add Tags", hook: hooks.useAddComedianModal },
    ],
    CLUB: [
        { key: "tags", label: "Add Tags", hook: hooks.useAddClubTagModal },
        { key: "scrape", label: "Run Scrape", hook: hooks.useRunScrapeModal },
        { key: "clear", label: "Clear SHows", hook: hooks.useClearShowsModal },
    ],
    SHOW: [
        { key: "tags", label: "Add Tags", hook: hooks.useAddShowTagModal },
        { key: "comedian", label: "Add Comedian", hook: hooks.useAddComedianModal },
    ],
};
