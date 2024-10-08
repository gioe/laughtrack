import * as searchController from '../../controllers/search/index.js'
import express, { Request, Response } from "express";
import bodyParser from "body-parser";

export const searchApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

searchApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {
        const { location, startDate, endDate, page, pageSize, sort} = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const result = await searchController.getHomeSearchResults({
            location, start_date: startDate, end_date: endDate
        }, sort);

        const dates = result?.dates ?? []

        const paginatedResults = dates.slice(startIndex, endIndex);
        const totalPages = Math.ceil(dates.length / pageSizeInt);

        return res.status(200).send({
            entity: {
                name: location,
                dates: paginatedResults
            },
            totalPages: isNaN(totalPages) ? 0 : totalPages
        })
    })