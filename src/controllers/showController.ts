import { Request, Response } from 'express';
import { getComedianShowDocuments } from '../util/storage/dataStore.js';

export const getShowsForComic = async (req: Request, res: Response) => {
  const name = req.params.name;
    res.json({
        shows: await getComedianShowDocuments(name)
      });
};