import * as showController from '../controllers/show/index.js'
import express, { Request, Response} from "express"; 
import { CreateShowDTO } from "../dto/show.dto.js";
import { authenticateRole, verifyToken } from '../middleware/auth.middleware.js';
import { UserRole } from '../../types/UserRole.js';

export const showsApiRouter = express.Router();

// POST items

showsApiRouter.get('/', 
    verifyToken, 
    authenticateRole(UserRole.Admin),  
    async (req: Request, res: Response) => {
    const results = await showController.getAll()
    return res.status(200).send(results)
})

showsApiRouter.get('/:name', 
    verifyToken, 
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await showController.getById(id)
    return res.status(200).send(result)
})

showsApiRouter.delete('/:id', 
    verifyToken, 
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await showController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

showsApiRouter.post('/', 
    verifyToken, 
    authenticateRole(UserRole.Admin), 
    async (req: Request, res: Response) => {
    const payload: CreateShowDTO = req.body
    const result = await showController.create(payload)
    return res.status(200).send(result)
})

showsApiRouter.delete('/', verifyToken, authenticateRole(UserRole.Admin), async (req: Request, res: Response) => {
    const result = await showController.deleteOldShows()
    return res.status(204).send({
        success: result
    })
})