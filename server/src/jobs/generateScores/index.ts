import * as showController from '../../api/controllers/show/index.js'
import * as comedianController from '../../api/controllers/comedian/index.js'
import * as clubController from '../../api/controllers/club/index.js'

async function setScores() {
    comedianController.generateScores()
    .then(() => showController.generateScores())
    .then(() => clubController.generateScores())
}

setScores();
