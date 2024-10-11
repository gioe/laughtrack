import * as searchController from '../../controllers/search/index.js'
import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { ShowInterface } from '../../../common/interfaces/client/show.interface.js';
import { toGetHomeSearchResultsDTO } from '../../../common/util/mappers/search/mapper.js';

export const searchApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

searchApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {
        const { location, startDate, endDate, page, pageSize} = req.body;

        if (location == 'undefined' || startDate == 'undefined' || endDate == 'undefined') { {
            return res.status(401).json({ error: 'Required fields missing' })
        }}

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;
        const dto = toGetHomeSearchResultsDTO(req.body)

        const result = await searchController.getHomeSearchResults(dto);

        const dates = result?.dates ?? []

        const paginatedResults = dates.slice(startIndex, endIndex);
        const totalPages = Math.ceil(dates.length / pageSizeInt);

        return res.status(200).send({
            entity: {
                name: location,
                dates: paginatedResults
            },
            clubs: result?.clubs ?? [],
            totalPages: isNaN(totalPages) ? 0 : totalPages,
            totalShows: dates.length
        })
        
    })