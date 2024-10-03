import { ComedianDetailsInterface, ComedianInterface, ComedianPopularityScore } from "../../../common/interfaces/comedian.interface.js"
import { generateComedianPopularityScore } from "../../util/scoringUtil.js"
import { db } from '../../../database/index.js';
import { IComedian, IComedianDetails, IComedianPopularityData } from "../../../database/models.js"
import { readFile } from "../../util/storageUtil.js";
import { JSON_KEYS } from "../../../common/constants/keys.js";
import { toComedianDetailsInterface, toComedianInterface } from "../../util/mappers/comedian/mapper.js";

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

export const getAllComedians = async (query?: string): Promise<ComedianInterface[]> => {
    return db.comedians.all().then((comedians: IComedian[]) => {
        return comedians.filter((comedian: IComedian) => {
            if (query) return comedian.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())
            return true
        }).map((comedian: IComedian) => toComedianInterface(comedian))
    })
}

export const getById = async (id: number): Promise<IComedian | null> => {
    return db.comedians.findById(id)
}

export const getByName = async (name: string): Promise<ComedianDetailsInterface | null> => {
    return db.comedians.findByName(name).then((response: IComedianDetails | null) => {
        if (response) return toComedianDetailsInterface(response)
        return null
    })
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


export const favoriteComedian = async (name: string, id: number): Promise<ComedianDetailsInterface | null> => {
    return db.comedians.findByName(name).then((response: IComedianDetails | null) => {
        if (response) return toComedianDetailsInterface(response)
        return null
    })
}
