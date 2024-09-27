import * as comedianController from '../comedian/index.js'
import * as showComedianController from '../showComedian/index.js'
import * as showDal from "../../../database/dal/show.js"
import { CreateShowDTO, CreateShowOutput, GetFilteredShowsRequest, ShowScore } from '../../dto/show.dto.js'
import { ShowInterface } from "../../../common/interfaces/show.interface.js"

export const createAll = async (allShows: ShowInterface[]): Promise<CreateShowOutput[]> => {
    var responses: CreateShowOutput[] = []

    for (let i = 0; i < allShows.length; i++) {
        const show = allShows[i]
        const output = await create(show)
        responses.push(output)
    }

    return responses
}

export const create = async (show: ShowInterface): Promise<CreateShowOutput> => {
    const comedians = await comedianController.createAll(show.comedians ?? [])
    const showOutput = await showDal.createShow(show)
    await showComedianController.createRelationshipForComedians(comedians, showOutput.id)
    return showOutput;
}

export const getById = async (id: number): Promise<ShowInterface> => {
    return showDal.getShowById(id)
}

export const deleteById = async (id: number): Promise<boolean> => {
    return showDal.deleteShowById(id)
}

export const getAll = async (): Promise<ShowInterface[]> => {
    return showDal.getAllShows()
}

export const getAllShowsForClubs = async (clubIds: number[]): Promise<ShowInterface[]> => {
    return showDal.getAllShowsForClubs(clubIds)
}

export const getSearchResults = async (request: GetFilteredShowsRequest) => {
    return showDal.getSearchResults(request)
}

export const updateScores = async (scores: ShowScore[]) => {

    for (let i = 0; i < scores.length; i++) {
        const score = scores[i]
        await showDal.updateScore(score)
    }
    
}
