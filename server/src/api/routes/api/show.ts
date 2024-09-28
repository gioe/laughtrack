import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { groupByPropertyCount } from '../../util/groupUtil.js';
import { GetSearchResultsOutput } from '../../dto/comedian.dto.js';

export const showApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items

showApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send(result)
    })

showApiRouter.post('/search', urlencodedParser,
    async (req: Request, res: Response) => {        
        
        const shows = await showController.getSearchResults(req.body);
        return res.status(200).send({
            total: shows.length,
            results: shows,
        })
    })