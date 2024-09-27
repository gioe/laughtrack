import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from '../../@types/UserRole.js';
import { ShowInterface } from '../../../common/interfaces/show.interface.js';

export const showAdminRouter = express.Router();

showAdminRouter.get('/', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const results = await showController.getAll()
        return res.status(200).send(results)
    })

showAdminRouter.post('/',  assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const payload: ShowInterface = req.body
        const result = await showController.create(payload)
        return res.status(200).send(result)
    })
