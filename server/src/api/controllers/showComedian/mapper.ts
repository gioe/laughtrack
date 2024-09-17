import { ShowComedianInterface } from '../../../common/interfaces/showComedian.interface.js'
import { ShowComedianDetailOutput } from '../../dto/showComedian.dto.js'

export const toShowComedian = (payload: ShowComedianDetailOutput): ShowComedianInterface => {
  return {
    showId: payload.show_id,
    comedianId: payload.comedian_id
  }
}
