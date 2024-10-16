import * as showController from '../../controllers/show/index.js'
import * as tagController from '../../controllers/tag/index.js'

import bodyParser from "body-parser";
import express, { Request, Response } from "express";

export const showApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

showApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send({
            entity: result
        })
    })


showApiRouter.get('/tags/all', urlencodedParser,
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await tagController.getAllByType({
            type: 'show'
        })
        return res.status(200).send({
            tags: result
        })
    })
