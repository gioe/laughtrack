import { Request, Response } from 'express';
import { scrapeAllClubs } from '../scrapers/index.js';

export const runAllScrapers = (req: Request, res: Response) => {
    scrapeAllClubs()
    res.json({
        message: 'Running scrapers',
      });
};