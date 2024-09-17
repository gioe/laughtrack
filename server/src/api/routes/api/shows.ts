import * as showController from '../../controllers/show/index.js'
import express, { Request, Response } from "express";
import { CreateShowDTO } from "../../dto/show.dto.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from '../../@types/UserRole.js';

export const showsApiRouter = express.Router();
export const publicShowsApiRouter = express.Router();

// POST items

showsApiRouter.get('/:id', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send(result)
    })
