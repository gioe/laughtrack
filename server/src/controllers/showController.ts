import { Request, Response } from 'express';
import { getValueFromDocument } from '../util/storage/fireStore.js';

const SHOW_COLLECTION_NAME = 'shows'

export const getShowsForComic = async (req: Request, res: Response) => {
  const name = req.params.name;
  const comicShows = await getValueFromDocument(SHOW_COLLECTION_NAME, name, ["shows"]);
    res.json({
        shows: comicShows
      });
};