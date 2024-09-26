import * as clubController from "../../controllers/club/index.js"
import * as showController from "../../controllers/show/index.js"
import { ClubInterface } from "../../../common/interfaces/club.interface.js";
import { ShowInterface } from "../../../common/interfaces/show.interface.js";
import { runScraper } from "../../../common/functions/scraper.js";
import { writeLogToFile } from "../../../jobs/util/logUtil.js";

export const scrapeClub = async (id: number) => {
    const startDate = new Date()

    writeLogToFile(`Started all scraping jobs at ${startDate}`)

    await clubController.getById(id)
        .then((club: ClubInterface) => runScraper(club))
        .then((scrapedShows: ShowInterface[]) => showController.createAll(scrapedShows))

    writeLogToFile(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}