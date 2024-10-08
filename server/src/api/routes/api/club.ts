import * as clubController from "../../controllers/club/index.js"
import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { ClubInterface } from "../../../common/interfaces/client/club.interface.js";

export const clubApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

clubApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {

        const { id } = req.params;

        const page = req.header("page");
        const pageSize = req.header("pageSize")
        const sort = req.header("sort")

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const decodedName = decodeURI(id)

        const result = await clubController.getByName(decodedName, sort)
        const dates = result?.dates ?? []

        const paginatedDates = dates.slice(startIndex, endIndex);
        const totalPages = Math.ceil(dates.length / pageSizeInt);

        return res.status(200).send({
            entity: {
                name: id,
                dates: paginatedDates
            },
            totalPages: isNaN(totalPages) ? 0 : totalPages
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
        const { page, pageSize, query } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        var clubs: ClubInterface[] = await clubController.getAllClubs(query)

        const paginatedClubs = clubs.slice(startIndex, endIndex);
        const totalPages = Math.ceil(clubs.length / pageSizeInt);

        return res.status(200).send({
            clubs: paginatedClubs,
            totalPages
        })
    })
