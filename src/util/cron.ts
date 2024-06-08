import cron from 'node-cron'
import { scrapeAllClubs } from './scrapers/index.js';

export const scheduleScrapes = () => {
    cron.schedule('0 0 * * *', () => {
        scrapeAllClubs();
    });
}

