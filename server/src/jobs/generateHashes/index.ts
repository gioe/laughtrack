import * as comedianController from '../../api/controllers/comedian/index.js'
import { ComedianInterface, UpdateComedianHashDTO } from '../../common/models/interfaces/comedian.interface.js';
import { generateComedianHash } from '../../common/util/domainModels/comedian/hash.js';

async function generateHashes() {
    comedianController.getAllComedians()
    .then((comedians: ComedianInterface[]) => {

        const hashedComedians = comedians.map((comedian: ComedianInterface) => {
            return {
                id: comedian.id,
                uuid_id: generateComedianHash(comedian.name)
            }  as UpdateComedianHashDTO
        })

        return comedianController.writeHashes(hashedComedians)

    })
}

generateHashes();
