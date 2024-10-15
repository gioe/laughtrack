
import * as clubController from "../../api/controllers/club/index.js"
import * as scrapingController from  "../../api/controllers/scrape/index.js"

import { runScraper } from "../../common/functions/scraper.js";
import { ClubScrapingData } from "../../common/models/interfaces/club.interface.js";
import { ScrapingOutput } from "../../common/models/interfaces/scrape.interface.js";
import { writeLogToFile } from "../../common/util/logUtil.js";
import { flattenArrayList } from "../../common/util/primatives/arrayUtil.js";
import { runTasks } from "../../common/util/promiseUtil.js";

async function runScrapingJob() {
    const args = process.argv.slice(2);
    const idArg = args.find((arg) => arg.startsWith("--arg="));
    const idString = idArg ? idArg.split("=")[1] : "";
    const ids = idString ? idString.split(",") : []
    const idNumbers = ids.map((id: string) => Number(id))

    writeLogToFile("Running scraping job")
    scrapeClubs(idNumbers)
}

export const scrapeClubs = async (id: number[]) => {
    const startDate = new Date()
    writeLogToFile(`Started all scraping jobs at ${startDate}`);

    await clubController.getAllScrapingData()
        .then((clubs: ClubScrapingData[]) => {
            const jobs = clubs
            .filter((club: ClubScrapingData) =>  id.length > 0 ? id.includes(club.id) : true)
            .map((club: ClubScrapingData) => runScraper(club))
            return runTasks(jobs)
        })
        .then((scrapingOutput: ScrapingOutput[][]) => flattenArrayList(scrapingOutput))
        .then((scrapingOutput: ScrapingOutput[]) => scrapingController.storeOutput(scrapingOutput))

    writeLogToFile(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

runScrapingJob();
