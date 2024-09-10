import playwright from "playwright";
import { Scraper } from "../../jobs/classes/models/Scraper.js";
import { ClubInterface } from "../interfaces/club.interface.js";
import { ShowInterface } from "../interfaces/show.interface.js";
import { chromium } from 'playwright-extra'
import StealthPlugin from 'puppeteer-extra-plugin-stealth'

export const runScraper = async (club: ClubInterface): Promise<ShowInterface[]> => {
    chromium.use(StealthPlugin())
    return playwright.chromium.launch({ headless: false })
        .then(browser => browser.newContext())
        .then(browserContext => getScrapingJob(browserContext, club))
}

const getScrapingJob = (browserContext: playwright.BrowserContext, club: ClubInterface): Promise<ShowInterface[]> => {
    return new Scraper(club, browserContext).scrape()
};
