import * as comedianController from "../../controllers/comedian/index.js"
import express, { Request, Response } from "express";
import { CreateComedianDTO } from "../../dto/comedian.dto.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from "../../@types/UserRole.js";

export const comediansAdminRouter = express.Router();

comediansAdminRouter.get('/', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const results = await comedianController.getAll()
        return res.status(200).send(results)
    })

comediansAdminRouter.delete('/:id', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)

        const result = await comedianController.deleteById(id)
        return res.status(204).send({
            success: result
        })
    })

comediansAdminRouter.post('/', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const payload: CreateComedianDTO = req.body
        const result = await comedianController.create(payload)
        return res.status(200).send(result)
    })

comediansAdminRouter.post('/merge', assignUser, authenticateRole(UserRole.Admin),
    async (req: Request, res: Response) => {
        const persistantId = req.query.persistantId as string
        const mergedIds = req.query.mergedIds as string
        const result = await comedianController.merge({
            persistantId: Number(persistantId),
            mergedIds: mergedIds.split(",").map((id: string) => Number(id))
        })
        return res.status(200).send(result)
    })