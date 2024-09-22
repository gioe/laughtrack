import * as clubController from "../../controllers/club/index.js"
import * as showController from "../../controllers/show/index.js"
import express, { Request, Response } from "express";
import { groupByPropertyCount } from "../../util/groupUtil.js";
import { ClubInterface } from "../../../common/interfaces/club.interface.js";

export const clubApiRouter = express.Router();

clubApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await clubController.getById(id)
        return res.status(200).send(result)
    })

clubApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const trendingClubs = await clubController.getTrendingClubs()
        return res.status(200).send(trendingClubs)
    })