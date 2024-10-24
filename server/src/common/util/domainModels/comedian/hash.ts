import { CreateComedianDTO } from "../../../models/interfaces/comedian.interface.js";
import {Md5} from 'ts-md5';
import { removeNonAlphanumeric } from "../../primatives/stringUtil.js";

export const generateComedianHashes = (comedians: CreateComedianDTO[]): CreateComedianDTO[] => {
    return comedians.map((comedian: CreateComedianDTO) => {
        const cleanedString = removeNonAlphanumeric(comedian.name).toLocaleLowerCase()
        const hash = Md5.hashStr(cleanedString)
        return {
            name: comedian.name,
            uuid_id: hash
        }
    })

}