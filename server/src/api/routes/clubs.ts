import * as clubController from "../controllers/club/index.js"
import express, { Request, Response} from "express"; 
import { assignUser } from "../middleware/assignUser.middleware.js";
import { authenticateRole } from "../middleware/authenticateRole.middleware.js";
import { CreateClubDTO } from "../dto/club.dto.js";
import { UserRole } from "../@types/UserRole.js";

export const clubsApiRouter = express.Router();
clubsApiRouter.use(assignUser)
clubsApiRouter.use(authenticateRole(UserRole.Admin))

clubsApiRouter.get('/',
    async (req: Request, res: Response) => {
    const results = await clubController.getAll()
    return res.status(200).send(results)
})

clubsApiRouter.get('/:id',
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await clubController.getById(id)
    return res.status(200).send(result)
})

clubsApiRouter.delete('/:id', 
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await clubController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

clubsApiRouter.post('/', 
    async (req: Request, res: Response) => {
    const payload: CreateClubDTO = req.body
    const result = await clubController.create(payload)
    return res.status(200).send(result)
})

clubsApiRouter.post('/all', 
    async (req: Request, res: Response) => {
    await clubController.createAll()
    return res.status(200).send({
        success: true
    })
})