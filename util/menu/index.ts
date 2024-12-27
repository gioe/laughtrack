
import { EntityType } from "../../objects/enum";
import * as hooks from "../../hooks/modalState";

export const getMenuItemsForEntityType = (type: EntityType | undefined) => {
    if (type == undefined) return []
    switch (type) {
        case EntityType.Club:
            return [
                { key: "clear", label: "Clear Shows", hook: hooks.useClearShowsModal },
            ]
        case EntityType.Show:
            return [
                { key: "tags", label: "Add Tags", hook: hooks.useAddShowTagModal },
                { key: "comedian", label: "Add Comedian", hook: hooks.useModifyLineupModal },
            ]
        case EntityType.Comedian:
            return [
                { key: "social", label: "Edit Social Data", hook: hooks.useSocialDataModal },
                { key: "tags", label: "Add Tags", hook: hooks.useAddEntityTagModal },
            ]
    }
}
