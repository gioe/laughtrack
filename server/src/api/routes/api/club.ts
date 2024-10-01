import * as clubController from "../../controllers/club/index.js"
import express, { Request, Response } from "express";
import bodyParser from "body-parser";

export const clubApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

clubApiRouter.post('/', urlencodedParser,
    async (req: Request, res: Response) => {
        const { name } = req.body;
        const decodedName = decodeURI(name)
        console.Console
        const result = await clubController.getByName(decodedName)
        return res.status(200).send(result)
    })

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

    clubApiRouter.post('/cities',
        async (req: Request, res: Response) => {
            const trendingClubs = await clubController.getAllCities()
            return res.status(200).send(trendingClubs)
        })