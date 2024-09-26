import { DATABASE } from "../constants/database.js"
import {
    create,
    deleteWithCondition,
    executeQuery,
    getAll,
    upsertAndDoNothing
} from "../util/queryUtil.js"
import { CreateShowComedianDTO, CreateShowComedianOutput, ShowComedianDetailOutput } from "../../api/dto/showComedian.dto.js"
import { GetShowDetailsOutput } from "../../api/dto/show.dto.js"
import { toShowComedian } from "../../api/controllers/showComedian/mapper.js"
import { GetShowPopularityDetailsOutput, ShowComedianInterface } from "../../common/interfaces/showComedian.interface.js"


export const createShowComedianRelationship = async (payload: CreateShowComedianDTO): Promise<CreateShowComedianOutput> => {
    return upsertAndDoNothing(DATABASE.SHOW_COMEDIANS_TABLE,
        `(show_id, comedian_id) VALUES($1, $2)`,
        `(show_id, comedian_id)`,
        [payload.showId, payload.comedianId])
}

export const getAllShowsForComedian = async (comedianId: number): Promise<GetShowDetailsOutput[]> => {
    const queryString = `
    SELECT * FROM ${DATABASE.SHOW_COMEDIANS_TABLE} cs INNER JOIN ${DATABASE.SHOWS_TABLE} s ON s.id = cs.show_id WHERE cs.comedian_id = $1;
    `
    const shows = await executeQuery<GetShowDetailsOutput>(queryString, [comedianId])
    return shows
}

export const deleteAllRelationshipsByShows = async (showIds: number[]): Promise<boolean> => {
    return deleteWithCondition(DATABASE.SHOW_COMEDIANS_TABLE, `show_id = ANY($1::int[])`, [showIds])
}

export const deleteAllRelationshipsByComedians = async (comedianIds: number[]): Promise<boolean> => {
    return deleteWithCondition(DATABASE.SHOW_COMEDIANS_TABLE, `comedian_id = ANY($1::int[])`, [comedianIds])
}

export const getAllShowComedians = async (): Promise<ShowComedianInterface[]> => {
    return getAll<ShowComedianDetailOutput>(DATABASE.SHOW_COMEDIANS_TABLE)
        .then((queryResponse: ShowComedianDetailOutput[]) => {
            return queryResponse.map((object: ShowComedianDetailOutput) => toShowComedian(object))
        })
}

export const getAllShowPopularityDetails = async (): Promise<GetShowPopularityDetailsOutput[]> => {
    const queryString = `
    SELECT show_id, instagram_followers as instagramFollowers, tiktok_followers as tikTokFollowers, is_pseudonym as isPseudonym
    FROM ${DATABASE.SHOW_COMEDIANS_TABLE} cs 
    INNER JOIN ${DATABASE.COMEDIANS_TABLE} c ON c.id = cs.comedian_id 
    INNER JOIN ${DATABASE.SHOWS_TABLE} s ON cs.show_id = s.id 
    `
    return await executeQuery<GetShowPopularityDetailsOutput>(queryString)
}
