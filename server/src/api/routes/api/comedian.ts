import * as comedianController from "../../controllers/comedian/index.js"
import express, { Request, Response } from "express";
import bodyParser from "body-parser";

export const comedianApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

comedianApiRouter.post('/favorite/:id', 
    urlencodedParser,

    async (req: Request, res: Response) => {
        const { id } = req.params;
        const idNumber = Number(id)

        if (idNumber == 0) return res.status(400).json({ error: "Comedian doesn't exist." });
        
        const result = await comedianController.favoriteComedian({
            comedian_id: idNumber,
            user_id: 1
        })

        return res.status(200).send(result)
    })

comedianApiRouter.get('/:name', urlencodedParser,
    async (req: Request, res: Response) => {
        const { name } = req.params;
        const decodedName = decodeURI(name)
        console.log(decodedName)
        const result = await comedianController.getByName(decodedName)
        console.log(result)
        return res.status(200).send(result)
    })

comedianApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const trendingComedians = await comedianController.getTrendingComedians()
        return res.status(200).send(trendingComedians)
    })

comedianApiRouter.post('/all', urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize, query } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        // Calculate the start and end indexes for the requested page
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const comedians = await comedianController.getAllComedians(query)

        // Slice the products array based on the indexes
        const paginatedComedians = comedians.slice(startIndex, endIndex);

        // Calculate the total number of pages
        const totalPages = Math.ceil(comedians.length / pageSizeInt);
        return res.status(200).send({
            comedians: paginatedComedians,
            totalPages
        })
    })