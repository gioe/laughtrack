import playwright from "playwright";
import StealthPlugin from 'puppeteer-extra-plugin-stealth'
import { chromium } from 'playwright-extra'
import { Scraper } from "../models/Scraper.js";
import { CreateShowDTO } from "../interfaces/data/show.interface.js";
import { ClubInterface } from "../interfaces/client/club.interface.js";

export const runScraper = async (club: ClubInterface): Promise<CreateShowDTO[]> => {
    chromium.use(StealthPlugin())
    return playwright.chromium.launch({ headless: true })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubInterface): Promise<CreateShowDTO[]> => {
    return new Scraper(club, browser).scrape()
};
