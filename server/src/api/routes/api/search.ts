import * as searchController from '../../controllers/search/index.js'

import bodyParser from "body-parser";
import express, { Request, Response } from "express";
import { toGetHomeSearchResultsDTO } from '../../../common/util/domainModels/search/mapper.js';
import { toPaginatedData } from '../../../common/util/domainModels/pagination/mapper.js';

export const searchApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

searchApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {
        const { location, startDate, endDate, page, pageSize } = req.body;

        if (location == 'undefined' || startDate == 'undefined' || endDate == 'undefined') {
            {
                return res.status(401).json({ error: 'Required fields missing' })
            }
        }

        const dto = toGetHomeSearchResultsDTO(req.body)

        const result = await searchController.getHomeSearchResults(dto);
        const dates = result?.dates ?? []
        const clubs = result?.clubs ?? []

        const paginationData = toPaginatedData(dates, page, pageSize)

        return res.status(200).send({
            entity: {
                name: location,
                dates: paginationData.data
            },
            clubs,
            totalPages: paginationData.totalPages,
            totalShows: dates.length
        })

    })