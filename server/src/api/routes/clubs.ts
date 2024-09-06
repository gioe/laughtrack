import * as clubController from "../controllers/club/index.js"
import * as storage from "../../common/storage.js"
import express, { Request, Response} from "express"; 
import { CreateClubDTO } from "../dto/club.dto.js";
import { authenticateRole, verifyToken } from "../middleware/auth.middleware.js";
import { UserRole } from "../../types/UserRole.js";

export const clubsApiRouter = express.Router();

clubsApiRouter.get('/', 
    verifyToken, 
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    const results = await clubController.getAll()
    return res.status(200).send(results)
})

clubsApiRouter.get('/:id',
    verifyToken,
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await clubController.getById(id)
    return res.status(200).send(result)
})

clubsApiRouter.delete('/:id', 
    verifyToken, 
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await clubController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

clubsApiRouter.post('/', 
    verifyToken,     
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    const payload: CreateClubDTO = req.body
    const result = await clubController.create(payload)
    return res.status(200).send(result)
})

clubsApiRouter.post('/all', 
    verifyToken,    
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    
    const clubs = await storage.getClubs();
    await clubController.createAll(clubs)
    return res.status(200).send({
        success: true
    })
})