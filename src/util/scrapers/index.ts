import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../../types/configs.interface.js";
import { ComedyCellarScaper } from "./comedyCellar.js";
import { readJsonFile } from "../storage/fileSystem.js";

const getScraper = (clubConfig: HTMLConfigurable) => {
    switch (clubConfig.scraper) {
        case "comedy_cellar": return new ComedyCellarScaper(clubConfig);
        default: undefined;
    }
}

export const scrapeAllClubs = async () => {
    console.log('Starting scraping job at:', new Date().toLocaleString());
    const clubs = readJsonFile(process.env.CLUBS_FILE ?? "src/clubs.json");

    for (const club of clubs) {
        const scraper = getScraper(club)

        if (scraper) {
            const browser = await puppeteer.launch({ dumpio: true });
            const page = await browser.newPage();        
            await scraper.scrape(page);
            await browser.close();
        }
    }
};