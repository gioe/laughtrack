import { Request, Response } from 'express';


export const runAllScrapers = (req: Request, res: Response) => {
 res.json({
   message: 'Running all scrapers',
 });
};


export const scrapeClub = (req: Request, res: Response) => {
 res.json({
   message: 'Another test route',
 });
};