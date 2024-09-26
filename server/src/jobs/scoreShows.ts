import * as showComedianController from '../api/controllers/showComedian/index.js'
import * as showController from '../api/controllers/show/index.js'
import { ShowScore } from '../api/dto/show.dto.js';
import { generateLocalDBConnection } from '../database/config.js';

async function setScores() {
    generateLocalDBConnection()
        .then(() => showComedianController.getAllShowPopularityDetails())
        .then((scores: ShowScore[]) => showController.updateScores(scores))
}


setScores();
