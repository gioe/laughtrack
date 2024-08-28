import * as showController from '../controllers/show/index.js'
import express, { Request, Response} from "express"; 
import { GetAllShowsFilters } from "../../database/dal/types.js";
import { CreateShowDTO } from "../dto/show.dto.js";

export const showsApiRouter = express.Router();

// POST items

showsApiRouter.get('/', async (req: Request, res: Response) => {
    const filters: GetAllShowsFilters = req.query
    const results = await showController.getAll(filters)
    return res.status(200).send(results)
})

showsApiRouter.get('/:name', async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await showController.getById(id)
    return res.status(200).send(result)
})

showsApiRouter.delete('/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await showController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

showsApiRouter.post('/',  async (req: Request, res: Response) => {
    const payload: CreateShowDTO = req.body
    const result = await showController.updateOrCreate(payload)
    return res.status(200).send(result)
})

