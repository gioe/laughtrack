import { ShowComedianInterface } from "../../../common/interfaces/showComedian.interface.js";
import * as showComedianDal from "../../../database/dal/showComedian.js"
 
export const getAllShowComedians = async (): Promise<ShowComedianInterface[]> => {
  return showComedianDal.getAllShowComedians();
}