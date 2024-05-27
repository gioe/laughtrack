import cron from 'node-cron'
import { scrapeComedyCellar } from "./scrapers/comedy_cellar.js";
import { ClubConfig } from "./types/index.js";
import { readJsonFile } from "./helpers/storage/files_system.js";


const scrapeData = async () => {
    console.log('Starting scraping job at:', new Date().toLocaleString());
    const clubs = readJsonFile('src/clubs.json');

    for (const config of clubs) {
        await scrapeClub(config);
    }
};

const scrapeClub = async (config: ClubConfig) => {
switch (config.scraper) {
    case "comedy_cellar": return await scrapeComedyCellar(config);
    default: return Promise.resolve();
}
};

cron.schedule('0 0 * * *', () => {
    scrapeData();
});