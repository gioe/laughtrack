import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import { CreateShowDTO } from "../../dto/show.dto.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from '../../@types/UserRole.js';
import bodyParser from "body-parser";

export const showsApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items

showsApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send(result)
    })


    showsApiRouter.post('/search', urlencodedParser,
    async (req: Request, res: Response) => {
        console.log("GOT SEARCH REQUEST")
        const { location, startDate, endDate} = req.body;
        
        // Get all the clubs at the location

        // Get all the shows at that club

        // Filter by the dates

        // Get all the comedians on those shows

        // Return list of comedians and shows
        
        return res.status(200).send({})
    })