import playwright from "playwright";
import { Scraper } from "../../jobs/classes/models/Scraper.js";
import { ClubInterface } from "../interfaces/club.interface.js";
import { ShowInterface } from "../interfaces/show.interface.js";

export const runScraper = async (club: ClubInterface): Promise<ShowInterface[]> => {
    return playwright.chromium.launch({ headless: false })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<ShowInterface[]> => {
    return new Scraper(club, browser).scrape()
};