import * as clubController from "../../api/controllers/club/index.js"
import * as showController from  "../../api/controllers/show/index.js"
import { ShowInterface } from "../../common/interfaces/show.interface.js";
import { ClubInterface } from "../../common/interfaces/club.interface.js";
import { runTasks } from "../../common/util/promiseUtil.js";
import { flatten } from "../../common/util/arrayUtil.js";
import { generateRemoteDBConnection } from "../../database/config.js";
import { runScraper } from "../../common/functions/scraper.js";

async function runScrapingJob() {
    console.log("Running scraping job")
    generateRemoteDBConnection()
    .then(() => showController.deleteOldShows()
    .then(() => scrapeAllClubs()))
}

export const scrapeClub = async (id: number) => {
    const startDate = new Date()

    console.log(`Started all scraping jobs at ${startDate}`);

    await clubController.getById(id)
        .then((club: ClubInterface) => runScraper(club))
        .then((scrapedShows: ShowInterface[]) => showController.createAll(scrapedShows))

    console.log(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

export const scrapeAllClubs = async () => {
    const startDate = new Date()

    console.log(`Started all scraping jobs at ${startDate}`);

    await clubController.getAll()
        .then((clubs: ClubInterface[]) => {
            const jobs = clubs.filter((club: ClubInterface) => club.name == 'Comedy Cellar New York').map((club: ClubInterface) => runScraper(club))
            return runTasks(jobs)
        })
        .then((scrapedShows: ShowInterface[][]) => flatten(scrapedShows))
        .then((scrapedShows: ShowInterface[]) => showController.createAll(scrapedShows))

    console.log(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

runScrapingJob();
