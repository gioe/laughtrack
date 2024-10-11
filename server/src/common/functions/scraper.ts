import playwright from "playwright";
import StealthPlugin from 'puppeteer-extra-plugin-stealth'
import { chromium } from 'playwright-extra'
import { Scraper } from "../models/Scraper.js";
import { ClubScrapingData } from "../models/interfaces/club.interface.js";
import { ScrapingOutput } from "../models/interfaces/scrape.interface.js";

export const runScraper = async (club: ClubScrapingData): Promise<ScrapingOutput[]> => {
    chromium.use(StealthPlugin())
    return playwright.chromium.launch({ headless: true })
        .then(browser => getScrapingJob(browser, club))
}

const getScrapingJob = (browser: playwright.Browser, club: ClubScrapingData): Promise<ScrapingOutput[]> => {
    return new Scraper(club, browser).scrape()
};
