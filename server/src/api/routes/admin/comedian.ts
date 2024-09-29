import * as comedianController from "../../controllers/comedian/index.js"
import express, { Request, Response } from "express";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from "../../@types/UserRole.js";
import { ComedianInterface } from "../../../common/interfaces/comedian.interface.js";

export const comedianAdminRouter = express.Router();

comedianAdminRouter.delete('/:id', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)

        const result = await comedianController.deleteById(id)
        return res.status(204).send({
            success: result
        })
    })

comedianAdminRouter.post('/', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const payload: ComedianInterface = req.body
        const result = await comedianController.create(payload)
        return res.status(200).send(result)
    })

comedianAdminRouter.post('/merge', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        return res.status(200).send({})
    })