import { ComedianInterface, ComedianPopularityScore } from "../../../common/interfaces/comedian.interface.js"
import { generateComedianPopularityScore } from "../../util/scoringUtil.js"
import { db } from '../../../database/index.js';
import { IComedian, IComedianPopularityData } from "../../../database/models.js"
import { readFile } from "../../util/storageUtil.js";
import { JSON_KEYS } from "../../../common/constants/keys.js";
import { toComedian } from "./mapper.js";

const getBadComedians = async (): Promise<string[]> => {
    return readFile(process.env.INVALID_COMEDIANS_FILE_NAME as string)
        .then((json: any) => {
            return json[JSON_KEYS.names].map((object: any) => {
                return object
            })
        })
}

export const createAll = async (comedians: ComedianInterface[]): Promise<null> => {
    const badComedians = await getBadComedians()

    const filteredComedians = comedians.filter((comedian: ComedianInterface) => !badComedians.includes(comedian.name))

    return db.comedians.addAll(filteredComedians);
}

export const create = async (payload: ComedianInterface): Promise<IComedian> => {
    return db.comedians.add(payload)
}

export const getAllComedians = async (): Promise<ComedianInterface[]> => {
    return db.comedians.all().then((comedians: IComedian[]) => comedians.map((comedian: IComedian) => toComedian(comedian)))
}

export const getById = async (id: number): Promise<IComedian | null> => {
    return db.comedians.findById(id)
}

export const getTrendingComedians = async (): Promise<IComedian[] | null> => {
    return db.comedians.getTrendingComedians()
}

export const deleteById = async (id: number): Promise<number> => {
    return db.comedians.remove(id)
}

export const generateScores = async (): Promise<null> => {
    const allData = await db.comedians.allPopularityData();
    if (!allData) return null

    const updatedValues = allData.map((data: IComedianPopularityData) => {
        return {
            id: data.id,
            popularity_score: generateComedianPopularityScore(data)
        }
    }) as ComedianPopularityScore[]

    return db.comedians.updateScores(updatedValues)
}
