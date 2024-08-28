import cron from 'node-cron'
import { scrapeAllClubs } from '../api/controllers/scraper/index.js';

export const scheduleScrapes = () => {
    cron.schedule('0 0 * * *', () => {
        scrapeAllClubs();
    });
}

