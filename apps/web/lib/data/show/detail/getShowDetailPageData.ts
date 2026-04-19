import { findRelatedShowsForShow } from "./findRelatedShowsForShow";
import { findShowById } from "./findShowById";
import { ShowDetailResponse } from "./interface";

export async function getShowDetailPageData(
    id: number,
): Promise<ShowDetailResponse> {
    const { show, clubId } = await findShowById(id);
    const relatedShows = await findRelatedShowsForShow(id, clubId);
    return { show, relatedShows };
}
