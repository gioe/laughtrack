import * as clubController from "../../api/controllers/club/index.js"
import { uploadFileToBucket } from "../../common/util/storageUtil.js";

async function writeClubs() {
   await uploadFileToBucket(process.env.CLUBS_FILE_NAME as string)
   await clubController.addAll()
}

writeClubs();
