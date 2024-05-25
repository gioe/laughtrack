import fs from "fs";
import { scrapeComedyCellar } from "./scrapers/comedy_cellar.js";
import { ClubConfig } from "./types/index.js";


const scrapeData = async () => {
    const clubs = readJsonFile();

    for (const config of clubs) {
        await scrapeClub(config);
    }
};

const readJsonFile = () => {
    try {
        const data = fs.readFileSync('src/clubs.json', 'utf8');
        return JSON.parse(data);
    } catch (err) {
        console.error('Error reading file:', err);
    }
};

const scrapeClub = async (config: ClubConfig) => {
    
switch (config.scraper) {
    case "comedy_cellar": return await scrapeComedyCellar(config);
    default: return Promise.resolve();
}
};


scrapeData();