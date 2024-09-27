import * as clubController from "../api/controllers/club/index.js"
import * as showController from  "../api/controllers/show/index.js"
import { ShowInterface } from "../common/interfaces/show.interface.js";
import { ClubInterface } from "../common/interfaces/club.interface.js";
import { runTasks } from "../common/util/promiseUtil.js";
import { flatten } from "../common/util/arrayUtil.js";
import { generateLocalDBConnection } from "../database/config.js";
import { runScraper } from "../common/functions/scraper.js";
import { writeLogToFile } from "./util/logUtil.js";

async function runScrapingJob() {
    const args = process.argv.slice(2);
    const idArg = args.find((arg) => arg.startsWith("--arg="));
    const idString = idArg ? idArg.split("=")[1] : "";
    const ids = idString ? idString.split(",") : []
    const idNumbers = ids.map((id: string) => Number(id))

    writeLogToFile("Running scraping job")
    generateLocalDBConnection()
    .then(() => scrapeClubs(idNumbers))
}

export const scrapeClubs = async (id: number[]) => {
    const startDate = new Date()
    writeLogToFile(`Started all scraping jobs at ${startDate}`);

    await clubController.getAll()
        .then((clubs: ClubInterface[]) => {
            const jobs = clubs.filter((club: ClubInterface) => {
                if (id.length > 0) return id.includes(club.id)
                return true
            })
            .map((club: ClubInterface) => runScraper(club))
            return runTasks(jobs)
        })
        .then((scrapedShows: ShowInterface[][]) => flatten(scrapedShows))
        .then((scrapedShows: ShowInterface[]) => showController.createAll(scrapedShows))

    writeLogToFile(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

runScrapingJob();
