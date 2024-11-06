"use server";

import { getDB } from "../../database";
import { SearchParams } from "../../objects/interfaces";
import { EntityType } from "../../util/enum";
const { db } = getDB();

export async function search(entityType: EntityType, params: SearchParams) {
    console.log("GETTING SEARCH RESULTS");

    return await db.search.getSearchResults(entityType, {});
}
