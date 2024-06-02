import cron from 'node-cron'
import { scrapeComedyCellar } from "../util/comedy_cellar.js";
import { ClubConfig } from "../types/configs.interface.js";
import { readJsonFile } from "../util/files_system.js";


const scrapeClub = async (config: ClubConfig) => {
    switch (config.scraper) {
        case "comedy_cellar": return await scrapeComedyCellar(config);
        default: return Promise.resolve();
    }
};

const scrapeData = async () => {
    console.log('Starting scraping job at:', new Date().toLocaleString());
    const clubs = readJsonFile('src/clubs.json');

    for (const config of clubs) {
        await scrapeClub(config);
    }
};

export const scheduleScrapes = () => {
    console.log('Scheduling scrapes');
    cron.schedule('0 0 * * *', () => {
        scrapeData();
    });
}

