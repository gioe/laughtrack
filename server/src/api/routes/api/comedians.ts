import * as comedianController from "../../controllers/comedian/index.js"
import * as showComedianController from "../../controllers/showComedian/index.js"
import express, { Request, Response } from "express";
import { CreateComedianDTO } from "../../dto/comedian.dto.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from "../../@types/UserRole.js";
import { groupByPropertyCount } from "../../util/groupUtil.js";
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";

export const comediansApiRouter = express.Router();

comediansApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await comedianController.getById(id)
        return res.status(200).send(result)
    })

comediansApiRouter.get('/shows/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const comedian = await comedianController.getById(id)
        const shows = await comedianController.getAllShowsById(id)
        return res.status(200).send({
            name: comedian.name,
            count: shows.length,
            shows
        })
    })

comediansApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const showComedians = await showComedianController.getAllShowComedians()
        const groupedShows = groupByPropertyCount(showComedians, "comedianId")

        const topTen = Object.keys(groupedShows)
            .map((comedianId: string) => {
                const showArray = groupedShows[comedianId]
                const count = showArray.length
                return {
                    comedianId,
                    count
                }
            })
            .sort((a, b) => b.count - a.count)
            .slice(0, 10)

        const topTenIds = topTen.map((object: any) => Number(object.comedianId))

        const comedians = await comedianController.getAlComediansByIds(topTenIds)

        const comediansResponse = comedians.map((comedian: ComedianInterface) => {
            return {
                name: comedian.name,
                showCount: comedian.name,
                instagram: comedian.instagram,
                count: groupedShows[comedian.id].length
            }
        })

        return res.status(200).send(comediansResponse)

    })