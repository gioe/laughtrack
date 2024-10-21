import * as showController from '../../controllers/show/index.js'
import * as comedianController from '../../controllers/comedian/index.js'
import * as lineupController from '../../controllers/lineup/index.js'

import { ScrapingOutput } from "../../../common/models/interfaces/scrape.interface.js";
import { toCreateLineupItemDTOArray } from '../../../common/util/domainModels/lineupItem/mapper.js';
import { providedPromiseResponse } from '../../../common/util/promiseUtil.js';

export const storeOutput = async (all: ScrapingOutput[]): Promise<void> => {
    
    for (let index = 0; index < all.length - 1; index++) {
        await storeOutputInstance(all[index])
    }
}

export const storeOutputInstance = async (instance: ScrapingOutput): Promise<null> => {

    const show = await showController.add(instance.show)

    if (instance.comedians.length > 0) {
        const comedians = await comedianController.addAll(instance.comedians)
        const lineupItems = toCreateLineupItemDTOArray(comedians, show.id)
        return lineupController.addAll(lineupItems)
    }

    return providedPromiseResponse(null)

}
