import { Request, Response } from 'express';
import { scheduleScrapes, scrapeAllClubs } from '../util/cron.js';


export const runAllScrapers = (req: Request, res: Response) => {
    scrapeAllClubs()
    res.json({
        message: 'Running scrapers',
      });
};