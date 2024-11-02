import * as showController from "../../controllers/show";
import * as comedianController from "../../controllers/comedian/";
import * as clubController from "../../controllers/club/";

async function setScores() {
    comedianController
        .generateScores()
        .then(() => showController.generateScores())
        .then(() => clubController.generateScores());
}

setScores();
