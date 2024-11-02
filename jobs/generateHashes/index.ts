import * as comedianController from "../../controllers/comedian";

import { ComedianInterface, UpdateComedianHashDTO } from "../../interfaces";
import { generateComedianHash } from "../../util/domainModels/comedian/hash";

async function generateHashes() {
    comedianController
        .getAllComedians()
        .then((comedians: ComedianInterface[]) => {
            const hashedComedians = comedians.map(
                (comedian: ComedianInterface) => {
                    return {
                        id: comedian.id,
                        uuid_id: generateComedianHash(comedian.name),
                    } as UpdateComedianHashDTO;
                },
            );

            return comedianController.writeHashes(hashedComedians);
        });
}

generateHashes();
