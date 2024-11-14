
import { EntityType } from "../../objects/enum";
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
        { key: "tags", label: "Add Tags", hook: hooks.useAddEntityTagModal },
        // { key: "merge", label: "Merge Comedians", hook: hooks.useMergeComediansModal },
    ],
    CLUB: [
        { key: "scrape", label: "Run Scrape", hook: hooks.useRunScrapeModal },
        { key: "clear", label: "Clear Shows", hook: hooks.useClearShowsModal },
    ],
    SHOW: [
        { key: "tags", label: "Add Tags", hook: hooks.useAddShowTagModal },
        { key: "comedian", label: "Add Comedian", hook: hooks.useModifyLineupModal },
        { key: "scrape", label: "Run Scrape", hook: hooks.useRunScrapeModal },
    ],
};
