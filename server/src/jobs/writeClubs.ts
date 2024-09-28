import * as clubController from "../api/controllers/club/index.js"

async function writeClubs() {
   await clubController.addAll()
}

writeClubs();
