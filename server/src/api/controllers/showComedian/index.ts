import { ShowComedianInterface } from "../../../common/interfaces/showComedian.interface.js";
import * as showComedianDal from "../../../database/dal/showComedian.js"
import { GetShowComedianDetailsOutput } from "../../dto/comedian.dto.js";
 
export const getAllShowComedians = async (): Promise<ShowComedianInterface[]> => {
  return showComedianDal.getAllShowComedians();
}

export const getAllComediansOnShows = async (showIds: number[]): Promise<GetShowComedianDetailsOutput[]> => {
  return showComedianDal.getAllComediansOnShows(showIds);
}
