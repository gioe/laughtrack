import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { IShowSearchResult } from '../../../database/models.js';

export const searchApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items
searchApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        // Calculate the start and end indexes for the requested page
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const results = await showController.getSearchResults(req.body);

        // Slice the products array based on the indexes
        const paginatedResults = results.slice(startIndex, endIndex);

        // Calculate the total number of pages
        const totalPages = Math.ceil(results.length / pageSizeInt);


        return res.status(200).send({
            city: req.body.location,
            shows: paginatedResults,
            totalPages
        })
    })