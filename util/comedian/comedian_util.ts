import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

export function combineComedianResults(comedians: any[]) {
    // First, create a map to group comedians by their effective ID
    const comedianMap = new Map();

    comedians.forEach(comedian => {
        // If this is a child comedian (has a parent)
        if (comedian.parentComedian) {
            const parentId = comedian.parentComedian.id;

            if (!comedianMap.has(parentId)) {
                // Store parent data if we haven't seen it yet
                comedianMap.set(parentId, {
                    ...comedian.parentComedian
                });
            }

        } else {
            // This is a parent comedian or standalone comedian
            if (!comedianMap.has(comedian.id)) {
                comedianMap.set(comedian.id, {
                    ...comedian,
                    lineupItems: [...comedian.lineupItems]
                });
            } else {
                // We've already created this record from a child, just add the lineup items
                const existingRecord = comedianMap.get(comedian.id);
                existingRecord.lineupItems = [
                    ...existingRecord.lineupItems,
                    ...comedian.lineupItems
                ];
                existingRecord.alternativeNames = comedian.alternativeNames;
            }
        }
    });

    // Convert map back to array and remove duplicates from lineup items
    return Array.from(comedianMap.values()).map(comedian => ({
        ...comedian
    }));
}
