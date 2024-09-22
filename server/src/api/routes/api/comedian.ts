import * as comedianController from "../../controllers/comedian/index.js"
import * as showComedianController from "../../controllers/showComedian/index.js"
import express, { Request, Response } from "express";
import { groupByPropertyCount } from "../../util/groupUtil.js";
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";

export const comedianApiRouter = express.Router();

comedianApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await comedianController.getById(id)
        return res.status(200).send(result)
    })

comedianApiRouter.get('/shows/:id',
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

comedianApiRouter.post('/trending',
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
                instagram: comedian.instagram,
                count: groupedShows[comedian.id].length
            }
        })

        return res.status(200).send(comediansResponse)

    })