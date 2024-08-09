import { Request, Response } from 'express';
import { getValueFromDocument, getValuesFromCollection } from '../util/storage/fireStore.js';
import { FIRESTORE_COLLECTIONS } from '../constants/firestore.js';
import { removeAllWhiteSpace } from '../util/types/stringUtil.js';
import { Show } from '../classes/Show.js';

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

export const getShowsForComedian = async (req: Request, res: Response) => {
  const name = req.query.name;
  const toDateString = req.query.to;
  const fromDateString = req.query.from;
  const toDate = new Date(toDateString as string);
  const fromDate = new Date(fromDateString as string);
  const documentName = removeAllWhiteSpace(name as string).toLowerCase()
  const comedianDoc = await getValueFromDocument(FIRESTORE_COLLECTIONS.comedians, documentName, ["name", "shows"]);

  var returnedShows: Show[] = []

  if (comedianDoc.get("shows")) {
    returnedShows = (comedianDoc.get("shows")).filter((show: any) => {
      const showDate = new Date(show.dateTime.seconds * 1000)
      return showDate >= fromDate && showDate <= toDate 
    })

  }

  res.json({
    comedian: {
      name, 
      shows: returnedShows
    }
  });

};