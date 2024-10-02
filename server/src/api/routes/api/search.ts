import * as searchController from '../../controllers/search/index.js'
import express, { Request, Response } from "express";
import bodyParser from "body-parser";

export const searchApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items
searchApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize, filter} = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        // Calculate the start and end indexes for the requested page
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const result = await searchController.getHomeSearchResults(req.body, filter);

        if (result) {
            const paginatedResults = result.shows.slice(startIndex, endIndex);

            // Calculate the total number of pages
            const totalPages = Math.ceil(result.shows.length / pageSizeInt);
    
    
            return res.status(200).send({
                city: result.city,
                shows: paginatedResults,
                totalPages, 
                totalShows: result.shows.length
            })
            
        }
        else {
            return res.status(200).send()
        }

    })