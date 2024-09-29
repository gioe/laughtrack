import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { IShowSearchResult } from '../../../database/models.js';

export const searchApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items
searchApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {        
        
        const response = await showController.getSearchResults(req.body);
        const top10 = response.slice(0,10)
        const coordinates = top10.map((result: IShowSearchResult) => JSON.stringify(result.coordinates));
        const uniqueCoordinates = [...new Set(coordinates)]

        return res.status(200).send({
            city: req.body.location,
            shows: top10,
            coordinates: uniqueCoordinates.flatMap((coordinateString: string) => JSON.parse(coordinateString))
        })
    })