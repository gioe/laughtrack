import playwright from "playwright";
import * as clubController from "../../controllers/club/index.js"
import * as showController from "../../controllers/show/index.js"
import { flatten } from "../../../util/arrayUtil.js";
import { Scraper } from "../../../database/models/Scraper.js";
import { Club } from "../../interfaces/club.interface.js";
import { runTasks } from "../../../util/promiseUtil.js";
import { Show } from "../../interfaces/show.interface.js";


export const scrapeClub = async (id: string) => {
    const startDate = new Date()

    console.log(`Started all scraping jobs at ${startDate}`);

    clubController.getById(id)
        .then((club: Club) => runScraper(club))
        .then((scrapedShows: Show[]) => showController.updateOrCreateAll([]))

    console.log(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

export const scrapeAllClubs = async () => {
    const startDate = new Date()

    console.log(`Started all scraping jobs at ${startDate}`);

    clubController.getAll({})
        .then((clubs: Club[]) => runScrapers(clubs))
        .then((scrapedShows: Show[]) => console.log(scrapedShows))

    console.log(`Finished in ${(new Date().getTime() - startDate.getTime()) / 1000} seconds`);
}

const runScrapers = async (clubs: Club[]): Promise<Show[]> => {
    return playwright.chromium.launch({ headless: true })
        .then(browser => {
            const jobs = clubs.map((club: Club) => new Scraper(club, browser).scrape())
            return runTasks(jobs)
        })
        .then((showArrays: Show[][]) => flatten(showArrays))
}

const runScraper = async (club: Club): Promise<Show[]> => {
    return playwright.chromium.launch({ headless: true })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: Club): Promise<Show[]> => {
    return new Scraper(club, browser).scrape()
};