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
        return res.status(200).send({
        })
    })

comedianApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const trendingComedians = await comedianController.getTrendingComedians()
        return res.status(200).send(trendingComedians)
    })

    comedianApiRouter.post('/all',
        async (req: Request, res: Response) => {
            const comedians = await comedianController.getAllComedians()
            return res.status(200).send(comedians)
        })