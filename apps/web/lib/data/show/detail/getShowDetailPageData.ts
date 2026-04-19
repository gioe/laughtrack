import { findRelatedShowsForShow } from "./findRelatedShowsForShow";
import { findShowById } from "./findShowById";
import { ShowDetailResponse } from "./interface";

export async function getShowDetailPageData(
    id: number,
): Promise<ShowDetailResponse> {
    const show = await findShowById(id);
    const relatedShows = await findRelatedShowsForShow(id, show.clubId);
    return { show, relatedShows };
}
