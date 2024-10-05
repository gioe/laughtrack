import { generateComedianPopularityScore } from "../../../common/util/scoringUtil.js"
import { db } from '../../../database/index.js';
import { toComedianInterface } from "../../../common/util/mappers/comedian/mapper.js";
import { ComedianInterface } from "../../../common/interfaces/client/comedian.interface.js";
import { CreateComedianDTO, GetComedianResponseDTO } from "../../../common/interfaces/data/comedian.interface.js";

export const addAll = async (comedians: CreateComedianDTO[]): Promise<{id: number}[]> => {
    return db.comedians.addAll(comedians);
}

export const getAllComedians = async (query?: string): Promise<ComedianInterface[]> => {
    return db.comedians.all().then((comedians: ComedianInterface[]) => {
        return comedians.filter((comedian: ComedianInterface) => {
            if (query) return comedian.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())
            return true
        }).map((comedian: ComedianInterface) => toComedianInterface(comedian))
    })
}

export const getByName = async (name: string): Promise<ComedianInterface | null> => {
    return db.comedians.findByName(name).then((response: GetComedianResponseDTO | null) => {
        if (response) return toComedianInterface(response)
        return null
    })
}

export const getTrendingComedians = async (): Promise<ComedianInterface[] | null> => {
    return db.comedians.getTrendingComedians()
}

export const generateScores = async (): Promise<null> => {
    const allData = await db.comedians.allPopularityData();
    if (!allData) return null

    const updatedValues = allData.map((data: any) => {
        return {
            id: data.id,
            popularity_score: generateComedianPopularityScore(data)
        }
    }) 

    return db.comedians.updateScores(updatedValues)
}


export const favoriteComedian = async (name: string, id: number): Promise<ComedianInterface | null> => {
    return null
}
