import * as clubController from "../../api/controllers/club/index.js"
import { downloadBucketContents } from "../../api/util/cloudStorageUtil.js";
import { isLocal } from "../../api/util/environmentUtil.js";
import { generateLocalDBConnection } from "../../database/config.js";

async function writeClubs() {

    generateLocalDBConnection()
    .then(() => clubController.createAll())
}

writeClubs();
