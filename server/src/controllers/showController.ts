import { Request, Response } from 'express';
import { getValueFromSpecificDocument } from '../util/storage/dataStore.js';

const SHOW_COLLECTION_NAME = 'shows'

export const getShowsForComic = async (req: Request, res: Response) => {
  const name = req.params.name;
  const comicShows = await getValueFromSpecificDocument(SHOW_COLLECTION_NAME, name, "shows");
    res.json({
        shows: comicShows
      });
};