import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import bodyParser from "body-parser";

export const showApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items

showApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send(result)
    })