import playwright from "playwright";
import StealthPlugin from 'puppeteer-extra-plugin-stealth'
import { ClubInterface } from "../interfaces/club.interface.js";
import { Scraper } from "../../jobs/classes/models/Scraper.js";
import { chromium } from 'playwright-extra'
import { IShow } from "../../database/models.js";

export const runScraper = async (club: ClubInterface): Promise<IShow[]> => {
    chromium.use(StealthPlugin())
    return playwright.chromium.launch({ headless: true })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<IShow[]> => {
    return new Scraper(club, browser).scrape()
};
