import * as comedianController from "../../controllers/comedian/index.js"
import express, { Request, Response } from "express";

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
        const trendingComedians = await comedianController.getTrendingComedians()
        return res.status(200).send(trendingComedians)
    })