import * as searchController from '../controllers/search/index.js'

import bodyParser from "body-parser";
import express, { Request, Response } from "express";
import { toGetHomeSearchResultsDTO } from '../../common/util/domainModels/search/mapper.js';
import { toPaginatedData } from '../../common/util/domainModels/pagination/mapper.js';
import { filterShows } from '../../common/util/domainModels/show/filter.js';
import { sortShows } from '../../common/util/domainModels/show/sort.js';

export const searchApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

searchApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {
        const { location, startDate, endDate, page, rows, query, sort, clubs } = req.body;
        if (location == 'undefined' || startDate == 'undefined' || endDate == 'undefined') {
            {
                return res.status(401).json({ error: 'Required fields missing' })
            }
        }

        const dto = toGetHomeSearchResultsDTO(req.body)

        const result = await searchController.getHomeSearchResults(dto);
        var dates = result?.dates ?? []
        const clubFilters = result?.clubs ?? []

        dates = filterShows(dates, {
            clubs: clubs,
            name: query
        })

        if (sort) {
            dates = sortShows(dates, sort)
        }

        const paginationData = toPaginatedData(dates, page, rows)

        return res.status(200).send({
            entity: {
                name: location,
                dates: paginationData.data
            },
            clubs: clubFilters,
            totalPages: paginationData.totalPages,
            totalShows: dates.length
        })

    })