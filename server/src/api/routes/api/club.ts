import * as clubController from "../../controllers/club/index.js"
import express, { Request, Response } from "express";
import bodyParser from "body-parser";

export const clubApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

clubApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;
        const decodedName = decodeURI(id)
        const result = await clubController.getByName(decodedName)
        return res.status(200).send({
            entity: {
                name: result?.name ?? id,
                dates: result?.shows ?? []
            },
            totalPages: 0
        })
    })

clubApiRouter.post('/cities',
    async (req: Request, res: Response) => {
        const trendingClubs: string[] = await clubController.getAllCities()
        return res.status(200).send(trendingClubs)
    })