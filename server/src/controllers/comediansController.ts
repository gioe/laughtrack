import { Request, Response } from 'express';
import { getAllComedianDocuments } from '../util/storage/dataStore.js';

export const getAllComedians = async (req: Request, res: Response) => {
    res.json({
        comedians: await getAllComedianDocuments(),
      });
};