import * as clubController from "../../controllers/club/index.js"
import express, { Request, Response } from "express";
import bodyParser from "body-parser";

export const clubApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

clubApiRouter.get('/:name', urlencodedParser,
    async (req: Request, res: Response) => {
        const { name } = req.params;
        const decodedName = decodeURI(name)
        const result = await clubController.getByName(decodedName)
        return res.status(200).send(result)
    })

clubApiRouter.post('/cities',
    async (req: Request, res: Response) => {
        const trendingClubs = await clubController.getAllCities()
        return res.status(200).send(trendingClubs)
    })