import { Request, Response } from 'express';
import { getValuesFromCollection } from '../util/storage/fireStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';

export const getAllComedians = async (req: Request, res: Response) => {
  const comedianDocs = await getValuesFromCollection(FIRESTORE_COLLECTIONS.comedians, ["name", "shows"])
  const comediansOrderedByShowCount = comedianDocs.sort((n1, n2) => {
    return n2.get("shows").length - n1.get("shows").length
  }).map(topFive => {
    return {
      docName:topFive.get("docName"),
      name: topFive.get("name"),
      showCount: topFive.get("shows").length
    }
  });
  
  res.json({
    comedians: comediansOrderedByShowCount,
  });
};
