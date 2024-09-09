

import playwright from "playwright";
import * as clubController from "../api/controllers/club/index.js"
import * as showController from  "../api/controllers/show/index.js"
import { ShowInterface } from "../common/interfaces/show.interface.js";
import { ClubInterface } from "../common/interfaces/club.interface.js";
import { runTasks } from "../common/util/promiseUtil.js";
import { flatten } from "lodash";
import { Scraper } from "./classes/models/Scraper.js";


async function scrapeAndDeleteShows() {
  showController.deleteOldShows()
  .then(() => scrapeAllClubs())
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
            const jobs = clubs.map((club: ClubInterface) => runScraper(club))
            return runTasks(jobs)
        })
        .then((scrapedShows: ShowInterface[][]) => flatten(scrapedShows))
        .then((scrapedShows: ShowInterface[]) => showController.createAll(scrapedShows))

    console.log(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

const runScraper = async (club: ClubInterface): Promise<ShowInterface[]> => {
    return playwright.chromium.launch({ headless: false })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<ShowInterface[]> => {
    return new Scraper(club, browser).scrape()
};


scrapeAndDeleteShows();
