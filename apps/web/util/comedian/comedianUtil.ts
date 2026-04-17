import { buildComedianImageUrl } from "../imageUtil";

export const filterAndMapLineupItems = (
    lineupItems: any[],
    userId?: string,
) => {
    // First, create a set of parent IDs that are present in the lineup
    const parentIdsInLineup = new Set(
        lineupItems
            .map((item) => {
                if (item.comedian.parentComedian == null) {
                    return item.comedian.id;
                }
            })
            .filter((item) => item !== undefined),
    );

    // Filter out children whose parents are in the lineup
    const filteredItems = lineupItems.filter((item) => {
        const hasParent = !!item.comedian.parentComedian;
        if (!hasParent) return true; // Keep all non-child comedians

        // Keep child only if their parent is not in the lineup
        return !parentIdsInLineup.has(item.comedian.parentComedian.id);
    });

    // Map the filtered items
    return filteredItems.map((item) => mapLineupItem(item, userId));
};

const mapLineupItem = (item: { comedian: any }, userId?: string) => {
    const effectiveComedian = getEffectiveComedian(item.comedian);
    const isAlias = containsAliasTag(effectiveComedian.taggedComedians ?? []);
    return {
        id: effectiveComedian.id,
        uuid: effectiveComedian.uuid,
        name: effectiveComedian.name,
        imageUrl: buildComedianImageUrl(
            effectiveComedian.name,
            effectiveComedian.hasImage,
        ),
        hasImage: Boolean(effectiveComedian.hasImage),
        isFavorite: userId
            ? (item.comedian.favoriteComedians?.length ?? 0) > 0
            : false,
        isAlias,
    };
};

export const containsAliasTag = (taggedComedians: any[]) => {
    return taggedComedians.some((tc) => tc.tag?.slug === "alias");
};

export const getEffectiveComedian = (comedian: any) =>
    comedian.parentComedian || comedian;
