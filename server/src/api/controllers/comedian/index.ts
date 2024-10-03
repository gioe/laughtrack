import { generateComedianPopularityScore } from "../../../common/util/scoringUtil.js"
import { db } from '../../../database/index.js';
import { readFile } from "../../../common/util/storageUtil.js";
import { JSON_KEYS } from "../../../common/constants/keys.js";
import { toComedianInterface } from "../../../common/util/mappers/comedian/mapper.js";
import { ComedianInterface } from "../../../common/interfaces/client/comedian.interface.js";
import { CreateComedianDTO } from "../../../common/interfaces/data/comedian.interface.js";

const getBadComedians = async (): Promise<string[]> => {
    return readFile(process.env.INVALID_COMEDIANS_FILE_NAME as string)
        .then((json: any) => {
            return json[JSON_KEYS.names].map((object: any) => {
                return object
            })
        })
}

export const createAll = async (comedians: CreateComedianDTO[]): Promise<null> => {
    const badComedians = await getBadComedians()

    const filteredComedians = comedians.filter((comedian: CreateComedianDTO) => !badComedians.includes(comedian.name))

    return db.comedians.addAll(filteredComedians);
}

export const getAllComedians = async (query?: string): Promise<ComedianInterface[]> => {
    return db.comedians.all().then((comedians: ComedianInterface[]) => {
        return comedians.filter((comedian: ComedianInterface) => {
            if (query) return comedian.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())
            return true
        }).map((comedian: ComedianInterface) => toComedianInterface(comedian))
    })
}

export const getById = async (id: number): Promise<ComedianInterface | null> => {
    return db.comedians.findById(id)
}

export const getByName = async (name: string): Promise<ComedianInterface | null> => {
    return db.comedians.findByName(name).then((response: ComedianInterface | null) => {
        if (response) return toComedianInterface(response)
        return null
    })
}

export const getTrendingComedians = async (): Promise<ComedianInterface[] | null> => {
    return db.comedians.getTrendingComedians()
}

export const deleteById = async (id: number): Promise<number> => {
    return db.comedians.remove(id)
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
    return db.comedians.findByName(name).then((response: ComedianInterface | null) => {
        if (response) return toComedianInterface(response)
        return null
    })
}
