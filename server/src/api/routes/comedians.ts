import * as comedianController from "../controllers/comedian/index.js"
import express, { Request, Response} from "express"; 
import { CreateComedianDTO, UpdateComedianDTO } from "../dto/comedian.dto.js";

export const comediansApiRouter = express.Router();

comediansApiRouter.get('/', async (req: Request, res: Response) => {
    const results = await comedianController.getAll()
    return res.status(200).send(results)
})

comediansApiRouter.get('/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await comedianController.getById(id)
    return res.status(200).send(result)
})


comediansApiRouter.get('/shows/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await comedianController.getAllShowsById(id)
    return res.status(200).send(result)
})

comediansApiRouter.delete('/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await comedianController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

comediansApiRouter.post('/',  async (req: Request, res: Response) => {
    const payload: CreateComedianDTO = req.body
    const result = await comedianController.create(payload)
    return res.status(200).send(result)
})