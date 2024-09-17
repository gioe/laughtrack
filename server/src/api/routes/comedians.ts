import * as comedianController from "../controllers/comedian/index.js"
import * as showComedianController from "../controllers/showComedian/index.js"
import express, { Request, Response } from "express";
import { CreateComedianDTO, MergeComedianDTO } from "../dto/comedian.dto.js";
import { assignUser } from "../middleware/assignUser.middleware.js";
import { authenticateRole } from "../middleware/authenticateRole.middleware.js";
import { UserRole } from "../@types/UserRole.js";
import { groupByPropertyCount } from "../util/groupUtil.js";
import { ComedianInterface } from "../../common/interfaces/comedian.interface.js";

export const publicComediansApiRouter = express.Router();
export const privateComediansApiRouter = express.Router();
privateComediansApiRouter.use(assignUser)
privateComediansApiRouter.use(authenticateRole(UserRole.Admin))

privateComediansApiRouter.get('/',
    async (req: Request, res: Response) => {
        const results = await comedianController.getAll()
        return res.status(200).send(results)
    })

    publicComediansApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await comedianController.getById(id)
        return res.status(200).send(result)
    })

    publicComediansApiRouter.get('/shows/:id',
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

    privateComediansApiRouter.delete('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)

        const result = await comedianController.deleteById(id)
        return res.status(204).send({
            success: result
        })
    })

privateComediansApiRouter.post('/',
    async (req: Request, res: Response) => {
        const payload: CreateComedianDTO = req.body
        const result = await comedianController.create(payload)
        return res.status(200).send(result)
    })

    privateComediansApiRouter.post('/merge',
    async (req: Request, res: Response) => {
        const persistantId = req.query.persistantId as string
        const mergedIds = req.query.mergedIds as string
        const result = await comedianController.merge({
            persistantId: Number(persistantId),
            mergedIds: mergedIds.split(",").map((id: string) => Number(id))
        })
        return res.status(200).send(result)
    })

publicComediansApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const showComedians = await showComedianController.getAllShowComedians()
        const groupedShows = groupByPropertyCount(showComedians, "comedianId")

        const topTen = Object.keys(groupedShows)
        .map((comedianId: string) => {
            const showArray = groupedShows[comedianId]
            const size = showArray.length
            return {
                comedianId,
                size
            }
        })
        .sort((a, b) => b.size - a.size)
        .slice(0, 10)

        const topTenIds = topTen.map((object: any) => Number(object.comedianId))

        return comedianController.getAlComediansByIds(topTenIds).then((clubs: ComedianInterface[]) => {
            const comediansResponse = clubs.map((comedian: ComedianInterface) => {
                return {
                    name: comedian.name,
                    showCount: comedian.name,
                    instagram: comedian.instagram,
                    count: groupedShows[comedian.id].length
                }
            })

            return res.status(200).send(comediansResponse)
        })
    })