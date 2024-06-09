import puppeteer from 'puppeteer';
import { HTMLConfigurable } from "../../types/configs.interface.js";
import { ComedyCellarScaper } from "./comedyCellar.js";
import { readJsonFile } from "../storage/fileSystem.js";
import { Club } from '../../types/club.interface.js';

const getScraper = (club: Club) => {
    switch (club.scraper) {
        case "comedy_cellar_vegas": return new ComedyCellarScaper(club);
        case "comedy_cellar_new_york": return new ComedyCellarScaper(club);
        default:  return undefined;
    }
}

export const scrapeAllClubs = async () => {
    console.log('Starting scraping job at:', new Date().toDateString());
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