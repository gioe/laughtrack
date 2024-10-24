import * as scrapeController from '../controllers/scrape/index.js'

import bodyParser from "body-parser";
import express, { Request, Response } from "express";

export const scrapeApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

scrapeApiRouter.post('/',
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { id, headless } = req.body;
        await scrapeController.scrapeClubs([Number(id)], headless)
        return res.status(200).send({
            success: true
        })
    })