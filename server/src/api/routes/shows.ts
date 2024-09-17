import * as showController from '../controllers/show/index.js'
import express, { Request, Response} from "express"; 
import { CreateShowDTO } from "../dto/show.dto.js";
import { assignUser } from "../middleware/assignUser.middleware.js";
import { authenticateRole } from "../middleware/authenticateRole.middleware.js";
import { UserRole } from '../@types/UserRole.js';

export const privateShowsApiRouter = express.Router();
export const publicShowsApiRouter = express.Router();

privateShowsApiRouter.use(assignUser)
privateShowsApiRouter.use(authenticateRole(UserRole.Admin))

// POST items

privateShowsApiRouter.get('/',  
    async (req: Request, res: Response) => {
    const results = await showController.getAll()
    return res.status(200).send(results)
})

publicShowsApiRouter.get('/:name', 
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await showController.getById(id)
    return res.status(200).send(result)
})

privateShowsApiRouter.delete('/:id',  
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await showController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

privateShowsApiRouter.post('/', 
    async (req: Request, res: Response) => {
    const payload: CreateShowDTO = req.body
    const result = await showController.create(payload)
    return res.status(200).send(result)
})
