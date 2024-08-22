import * as clubController from "../controllers/club/index.js"
import express, { Request, Response} from "express"; 
import { GetAllClubsFilters } from "../../database/dal/types.js";
import { CreateClubDTO, UpdateClubDTO } from "../dto/club.dto.js";

export const clubsApiRouter = express.Router();

clubsApiRouter.get('/', async (req: Request, res: Response) => {
    const filters: GetAllClubsFilters = req.query
    const results = await clubController.getAll(filters)
    return res.status(200).send(results)
})

clubsApiRouter.get(':/id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await clubController.getById(id)
    return res.status(200).send(result)
})

clubsApiRouter.put('/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const payload: UpdateClubDTO = req.body

    const result = await clubController.update(id, payload)
    return res.status(201).send(result)
})

clubsApiRouter.delete('/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await clubController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

clubsApiRouter.post('/',  async (req: Request, res: Response) => {
    const payload: CreateClubDTO = req.body
    const result = await clubController.create(payload)
    return res.status(200).send(result)
})