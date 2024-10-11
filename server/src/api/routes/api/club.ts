import * as clubController from "../../controllers/club/index.js"

import bodyParser from "body-parser";
import express, { Request, Response } from "express";
import { ClubInterface } from "../../../common/models/interfaces/club.interface.js";
import { toPaginatedData } from "../../../common/util/domainModels/pagination/mapper.js";

export const clubApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

clubApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {

        const { id } = req.params;

        const sort = req.header("sort")

        const decodedName = decodeURI(id)

        const result = await clubController.getByName(decodedName)
        const dates = result?.dates ?? []

        const page = req.header("page") as string;
        const pageSize = req.header("pageSize") as string
        const paginationData = toPaginatedData(dates, page, pageSize)

        return res.status(200).send({
            entity: {
                name: id,
                dates: paginationData.data
            },
            totalPages: paginationData.totalPages
        })
    })

clubApiRouter.post('/cities',
    async (req: Request, res: Response) => {
        const trendingClubs: string[] = await clubController.getAllCities()
        return res.status(200).send(trendingClubs)
    })

clubApiRouter.post('/all',
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize } = req.body;

        var clubs: ClubInterface[] = await clubController.getAllClubs()
        var cities: string[] = await clubController.getAllCities()

        const paginationData = toPaginatedData(clubs, page, pageSize)

        return res.status(200).send({
            clubs: paginationData.data,
            totalPages: paginationData.totalPages,
            totalClubs: clubs.length,
            cities
        })
    })
