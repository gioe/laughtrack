import playwright from "playwright";
import * as clubController from "../../controllers/club/index.js"
import * as showController from "../../controllers/show/index.js"
import { flatten } from "../../../util/arrayUtil.js";
import { runTasks } from "../../../util/promiseUtil.js";
import { Scraper } from "../../models/Scraper.js";
import { ClubInterface } from "../../interfaces/club.interface.js";
import { ShowInterface } from "../../interfaces/show.interface.js";

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
    return playwright.chromium.launch({ headless: true })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<ShowInterface[]> => {
    return new Scraper(club, browser).scrape()
};