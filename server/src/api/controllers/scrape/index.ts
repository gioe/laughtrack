import * as showController from '../../controllers/show/index.js'
import * as comedianController from '../../controllers/comedian/index.js'
import * as lineupController from '../../controllers/lineup/index.js'

import { ScrapingOutput } from "../../../common/models/interfaces/scrape.interface.js";
import { CreateLineupItemDTO } from '../../../common/models/interfaces/lineupItem.interface.js';

export const storeOutput = async (all: ScrapingOutput[]): Promise<void> => {

    for (let index = 0; index < all.length - 1; index++) {
        await storeOutputInstance(all[index])
    }
}

export const storeOutputInstance = async (instance: ScrapingOutput): Promise<null> => {
    
    const show = await showController.add(instance.show)
    const comedians = await comedianController.addAll(instance.comedians)

    const lineupItems = comedians.map((comedian: {id: number}) => {
        return {
            show_id: show.id,
            comedian_id: comedian.id
        }
    }) as CreateLineupItemDTO[]

    return lineupController.addAll(lineupItems)

}