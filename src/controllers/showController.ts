import { Request, Response } from 'express';

export const getShowsForBlah = (req: Request, res: Response) => {
    res.json({
        message: 'Running scrapers',
      });
};