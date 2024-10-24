import * as clubController from "../controllers/club/index.js"
import * as showController from "../controllers/show/index.js"

import bodyParser from "body-parser";
import express, { Request, Response } from "express";
import { ClubInterface } from "../../common/models/interfaces/club.interface.js";
import { toPaginatedData } from "../../common/util/domainModels/pagination/mapper.js";
import { sortShows } from "../../common/util/domainModels/show/sort.js";
import { sortClubs } from "../../common/util/domainModels/club/sort.js";
import { filterClubs } from "../../common/util/domainModels/club/filter.js";
import { filterShows } from "../../common/util/domainModels/show/filter.js";

export const clubApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

clubApiRouter.post('/all',
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize, sort, city, query } = req.body;

        var clubs: ClubInterface[] = await clubController.getAllClubs()
        const totalClubs = clubs.length
        var cities: string[] = await clubController.getAllCities()

        clubs = filterClubs(clubs, {
            city,
            name: query
        })

        if (sort) {
            clubs = sortClubs(clubs, sort)
        }

        const paginationData = toPaginatedData(clubs, page, pageSize)

        return res.status(200).send({
            clubs: paginationData.data,
            totalPages: paginationData.totalPages,
            totalClubs,
            cities
        })
    })


clubApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {

        const { id } = req.params;

        const sort = req.header("sort")
        const query = req.header("query")

        const decodedName = decodeURI(id)
        const result = await clubController.getByName(decodedName)
        var dates = result?.dates ?? []

        if (sort) {
            dates = sortShows(dates, sort)
        }

        dates = filterShows(dates, {
            name: query
        })

        const page = req.header("page") as string;
        const rows = req.header("rows") as string

        const paginationData = toPaginatedData(dates, page, rows)
        return res.status(200).send({
            entity: {
                id: result?.id,
                name: result?.name,
                socialData: result?.socialData,
                dates: paginationData.data
            },
            totalShows: dates.length,
            totalPages: paginationData.totalPages
        })
    })

clubApiRouter.get('/cities',
    async (req: Request, res: Response) => {
        const trendingClubs: string[] = await clubController.getAllCities()
        return res.status(200).send(trendingClubs)
    })


clubApiRouter.post('/clear', urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.body
        await showController.deleteShowsForClub(id)
        return res.status(200).send({
            success: true
        })
    })
