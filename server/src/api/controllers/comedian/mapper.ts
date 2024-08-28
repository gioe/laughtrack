import { ComedianOuput } from "../../../database/models/Comedian.js"
import { Comedian } from "../../interfaces/comedian.interface.js"

export const toComedian = (comedian: ComedianOuput): Comedian => {
    return {
        id: comedian.id,
        name: comedian.name
    }
}