import { ComedianInterface } from '../../../common/interfaces/comedian.interface.js'
import { GetComedianDetailsOutput } from '../../dto/comedian.dto.js'

export const toComedian = (payload: GetComedianDetailsOutput): ComedianInterface => {
    return {
        id: payload.id,
        name: payload.name,
        instagram: payload.instagram_account
    }
}
