import playwright from "playwright";
import { chromium } from 'playwright-extra'
import StealthPlugin from 'puppeteer-extra-plugin-stealth'
import { ClubInterface } from "../interfaces/club.interface.js";
import { ShowInterface } from "../interfaces/show.interface.js";
import { Scraper } from "../../jobs/classes/models/Scraper.js";
import { writeFailureToFile } from "../../jobs/util/logUtil.js";

export const runScraper = async (club: ClubInterface): Promise<ShowInterface[]> => {
    chromium.use(StealthPlugin())
    return playwright.chromium.launch({ headless: true })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<ShowInterface[]> => {
    return new Scraper(club, browser).scrape().then(((shows: ShowInterface[]) =>  {
        if (shows.length == 0) {
            writeFailureToFile(`No shows returned for ${club.name}`)
        }
        return shows
    }));
};
