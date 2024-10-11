import * as comedianController from "../../controllers/comedian/index.js"

import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { ComedianInterface } from "../../../common/models/interfaces/comedian.interface.js";
import { toGetComediansDTO } from "../../../common/util/domainModels/comedian/mapper.js";
import { UserRole } from "../../../common/models/@types/UserRole.js";

export const comedianApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

comedianApiRouter.post('/favorite/all',
    assignUser,
    authenticateRole([UserRole.Admin, UserRole.User]),
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;
        const { page, pageSize, query } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        // Calculate the start and end indexes for the requested page
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;
        const comedians = await comedianController.getAllFavorites(req.currentUser.id)
        const paginatedComedians = comedians.slice(startIndex, endIndex);
        const totalPages = Math.ceil(comedians.length / pageSizeInt);

        return res.status(200).send({
            comedians: paginatedComedians,
            totalPages
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
            user_id: req.currentUser.id,
            is_favorite: isFavorite == "1" ? true : false
        })

        return res.status(200).send(result)

    })

comedianApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;

        const page = req.header("page");
        const pageSize = req.header("pageSize");
        const sort = req.header("sort")

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const decodedName = decodeURI(id)

        const result = await comedianController.getByName(decodedName, sort)
        const dates = result?.dates ?? []

        const paginatedDates = dates.slice(startIndex, endIndex);
        const totalPages = Math.ceil(dates.length / pageSizeInt);

        return res.status(200).send({
            entity: {
                ...result,
                dates: paginatedDates
            },
            totalPages: isNaN(totalPages) ? 0 : totalPages
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
        const { page, pageSize } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const dto = toGetComediansDTO(req)

        var comedians: ComedianInterface[] = [];

        if (req.currentUser == undefined) {
            comedians = await comedianController.getAllComedians(dto)
        } else {
            comedians = await comedianController.getAllComediansWithFavorites(dto)
        }

        const paginatedComedians = comedians.slice(startIndex, endIndex);
        const totalPages = Math.ceil(comedians.length / pageSizeInt);

        return res.status(200).send({
            comedians: paginatedComedians,
            totalPages,
            totalComedians: comedians.length
        })
    })

comedianApiRouter.put('/social',
    assignUser,
    urlencodedParser,
    async (req: Request, res: Response) => {

        const response = await comedianController.updateSocialData(req.body)

        return res.status(200).send(response)
    })


