import * as showComedianDal from "../../../database/dal/showComedian.js"
import { GetShowDetailsOutput} from "../../dto/show.dto.js";
import { CreateShowComedianOutput } from "../../dto/showComedian.dto.js";
import {  ShowComedianInterface } from "../../../common/interfaces/showComedian.interface.js";
import { CreateComedianOutput } from "../../dto/comedian.dto.js";

export const createRelationshipForShows = async (comedianId: number, shows: GetShowDetailsOutput[]): Promise<CreateShowComedianOutput[]> => {
  const showIds = shows.map((show: GetShowDetailsOutput) => show.id)

  var responses: CreateShowComedianOutput[] = []

  for (let i = 0; i < showIds.length; i++) {
    const showComedianOutput = await create(showIds[i], comedianId)
    responses.push(showComedianOutput)
  }

  return responses
}

export const createRelationshipForComedians = async (comedians: CreateComedianOutput[], showId: number): Promise<CreateShowComedianOutput[]> => {
  const comedianIds = comedians.map((comedian: CreateComedianOutput) => comedian.id)

  var responses: CreateShowComedianOutput[] = []

  for (let i = 0; i < comedianIds.length; i++) {
    const comedianId = comedianIds[i]
    const showComedianOutput = await create(comedianId, showId)
    responses.push(showComedianOutput)
  }

  return responses
}

export const create = async (comedianId: number, showId: number): Promise<CreateShowComedianOutput> => {
  return showComedianDal.createShowComedianRelationship({ comedianId, showId })
}

export const getAllShowComedians = async (): Promise<ShowComedianInterface[]> => {
  return showComedianDal.getAllShowComedians();
}
