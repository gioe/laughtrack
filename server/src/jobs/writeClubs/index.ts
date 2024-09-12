import * as clubController from "../../api/controllers/club/index.js"
import { generateLocalDBConnection } from "../../database/config.js";

async function writeClubs() {

    generateLocalDBConnection()
    .then(() => clubController.createAll())
}

writeClubs();
