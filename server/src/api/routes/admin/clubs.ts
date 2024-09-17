import * as clubController from "../../controllers/club/index.js"
import express, { Request, Response } from "express";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from "../../@types/UserRole.js";

export const clubsAdminRouter = express.Router();

clubsAdminRouter.get('/', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const results = await clubController.getAll()
        return res.status(200).send(results)
    })


clubsAdminRouter.delete('/:id', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)

        const result = await clubController.deleteById(id)
        return res.status(204).send({
            success: result
        })
    })
