import { Request, Response } from 'express';

export const getAllComics = (req: Request, res: Response) => {
    res.json({
        message: 'Running scrapers',
      });
};