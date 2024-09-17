import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import { CreateShowDTO } from "../../dto/show.dto.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from '../../@types/UserRole.js';

export const showsAdminRouter = express.Router();

// POST items

showsAdminRouter.get('/', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const results = await showController.getAll()
        return res.status(200).send(results)
    })

showsAdminRouter.post('/',  assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const payload: CreateShowDTO = req.body
        const result = await showController.create(payload)
        return res.status(200).send(result)
    })
