import * as comedianController from "../../controllers/comedian/index.js"
import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from "../../../common/@types/UserRole.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { ComedianInterface } from "../../../common/interfaces/client/comedian.interface.js";

export const comedianApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

comedianApiRouter.post('/favorite/:id',
    assignUser,
    authenticateRole([UserRole.Admin, UserRole.User]),
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;
        
        if (id == 'all') {
            const { page, pageSize, query } = req.body;

            const pageInt = parseInt(page as string);
            const pageSizeInt = parseInt(pageSize as string);
    
            // Calculate the start and end indexes for the requested page
            const startIndex = (pageInt - 1) * pageSizeInt;
            const endIndex = pageInt * pageSizeInt;
            const comedians = await comedianController.getAllFavorites(req.currentUser.id)
            const paginatedComedians = comedians.slice(startIndex, endIndex);
            const totalPages = Math.ceil(comedians.length / pageSizeInt);
    
            return res.status(200).send({
                comedians: paginatedComedians,
                totalPages
            })   
        } else {
            const { isFavorite } = req.body;
            const idNumber = Number(id)
    
            if (idNumber == 0) return res.status(400).json({ error: "Comedian doesn't exist." });
    
            const result = await comedianController.favoriteComedian({
                comedian_id: idNumber,
                user_id: req.currentUser.id,
                is_favorite: isFavorite == "1" ? true : false
            })
            return res.status(200).send(result)
        }

    })

comedianApiRouter.get('/:name', urlencodedParser,
    async (req: Request, res: Response) => {
        const { name } = req.params;
        const decodedName = decodeURI(name)
        const result = await comedianController.getByName(decodedName)
        return res.status(200).send(result)
    })

comedianApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const trendingComedians = await comedianController.getTrendingComedians()
        return res.status(200).send(trendingComedians)
    })

comedianApiRouter.post('/all',
    assignUser,
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize, query } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        // Calculate the start and end indexes for the requested page
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        var comedians: ComedianInterface[] = [];

        if (req.currentUser == undefined) {
            comedians = await comedianController.getAllComedians(query)
        } else {
            comedians = await comedianController.getAllComediansWithFavorites(req.currentUser.id, query)
        }

        // Slice the products array based on the indexes
        const paginatedComedians = comedians.slice(startIndex, endIndex);

        // Calculate the total number of pages
        const totalPages = Math.ceil(comedians.length / pageSizeInt);
        
        return res.status(200).send({
            comedians: paginatedComedians,
            totalPages
        })
    })
