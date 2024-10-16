import * as comedianController from "../../controllers/comedian/index.js"

import bodyParser from "body-parser";
import express, { Request, Response } from "express";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { toGetComediansDTO } from "../../../common/util/domainModels/comedian/mapper.js";
import { UserRole } from "../../../common/models/@types/UserRole.js";
import { toPaginatedData } from "../../../common/util/domainModels/pagination/mapper.js";
import { toUpdateSocialDataDTO } from "../../../common/util/domainModels/socialData/mapper.js";
import { sortComedians } from "../../../common/util/domainModels/comedian/sort.js";
import { filterComedians } from "../../../common/util/domainModels/comedian/filter.js";

export const comedianApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

comedianApiRouter.post('/favorite/all',
    assignUser,
    authenticateRole([UserRole.Admin, UserRole.User]),
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize } = req.body;

        const comedians = await comedianController.getAllFavorites(req.currentUser.id)
        const paginationData = toPaginatedData(comedians, page, pageSize)

        return res.status(200).send({
            comedians: paginationData.data,
            totalPages: paginationData.totalPages
        })

    })

comedianApiRouter.post('/addToFavorites/:id',
    assignUser,
    authenticateRole([UserRole.Admin, UserRole.User]),
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;
        const { isFavorite } = req.body;
        const idNumber = Number(id)

        if (idNumber == 0) return res.status(400).json({ error: "Comedian doesn't exist." });

        const result = await comedianController.favoriteComedian({
            comedian_id: idNumber,
            user_id: req.currentUser.id
        }, isFavorite == "1")

        return res.status(200).send(result)

    })

comedianApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;

        const page = req.header("page") as string;
        const pageSize = req.header("pageSize") as string;
        const sort = req.header("sort")

        const decodedName = decodeURI(id)

        const result = await comedianController.getByName(decodedName)

        const dates = result?.dates ?? []

        const paginationData = toPaginatedData(dates, page, pageSize)

        return res.status(200).send({
            entity: {
                ...result,
                dates: paginationData.data
            },
            totalShows: paginationData.data.length,
            totalPages: paginationData.totalPages
        })
    })

comedianApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const trendingComedians = await comedianController.getTrendingComedians()
        return res.status(200).send(trendingComedians)
    })

comedianApiRouter.post('/all',
    assignUser,
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize, sort, query } = req.body;

        const dto = toGetComediansDTO(req)

        var comedians = await comedianController.getAllComedians(dto)

        comedians = filterComedians(comedians, {
            name: query
        })

        if (sort) {
            comedians = sortComedians(comedians, sort)
        }


        const paginationData = toPaginatedData(comedians, page, pageSize)

        return res.status(200).send({
            comedians: paginationData.data,
            totalPages: paginationData.totalPages,
            totalComedians: comedians.length
        })
    })

comedianApiRouter.put('/social',
    assignUser,
    urlencodedParser,
    async (req: Request, res: Response) => {
        const input = toUpdateSocialDataDTO(req.body)

        const response = await comedianController.updateSocialData(input)

        return res.status(200).send(response)
    })

comedianApiRouter.post('/filters/all',
    assignUser,
    urlencodedParser,
    async (req: Request, res: Response) => {
        var filters = await comedianController.getAllComedianFilters()
        const sortedFilters = filters.sort((a, b) => a.name < b.name ? -1 : 1)
        return res.status(200).send({
            filters: sortedFilters
        })
    })
