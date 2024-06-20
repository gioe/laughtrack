import { Request, Response } from 'express';
import { getValueFromAllDocuments } from '../util/storage/dataStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';

export const getAllComedians = async (req: Request, res: Response) => {
  const comedianDocs = await getValueFromAllDocuments(FIRESTORE_COLLECTIONS.comedians, "comedians")

  console.log(comedianDocs)

    res.json({
        comedians: comedianDocs,
      });
};

export const getTrendingComedians = async (req: Request, res: Response) => {
  const showCounts = await getValueFromAllDocuments(FIRESTORE_COLLECTIONS.comedians, "showCount")
  console.log(showCounts)

  res.json({
      comedians: showCounts,
    });
};
