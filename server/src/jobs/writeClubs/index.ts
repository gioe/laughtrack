

import * as clubController from "../../api/controllers/club/index.js"
import { downloadBucketContents } from "../../api/util/cloudStorageUtil.js";
import { isLocal } from "../../api/util/environmentUtil.js";
import { generateDBConnectionPool } from "../../database/config.js";

async function writeClubs() {

    if (isLocal) {
        await downloadBucketContents();
    }
    
    generateDBConnectionPool()
    .then(() => clubController.createAll())
}

writeClubs();
