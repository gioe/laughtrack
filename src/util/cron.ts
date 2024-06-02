import cron from 'node-cron'
import { scrapeComedyCellar } from "./comedyCellar.js";
import { HTMLConfigurable } from "../types/configs.interface.js";
import { readJsonFile } from "./storage/fileSystem.js";


export const scrapeClub = async (config: HTMLConfigurable) => {
    switch (config.scraper) {
        case "comedy_cellar": return await scrapeComedyCellar(config);
        default: return Promise.resolve();
    }
};

export const scrapeAllClubs = async () => {
    console.log('Starting scraping job at:', new Date().toLocaleString());
    const clubs = readJsonFile('src/clubs.json');

    for (const config of clubs) {
        await scrapeClub(config);
    }
};

export const scheduleScrapes = () => {
    scrapeAllClubs();

}

