import * as clubController from "../controllers/club/index.js"
import * as showController from "../controllers/show/index.js"
import express, { Request, Response } from "express";
import { assignUser } from "../middleware/assignUser.middleware.js";
import { authenticateRole } from "../middleware/authenticateRole.middleware.js";
import { UserRole } from "../@types/UserRole.js";
import { groupByPropertyCount } from "../util/groupUtil.js";
import { ClubInterface } from "../../common/interfaces/club.interface.js";

export const publicClubsApiRouter = express.Router();
export const privateClubsApiRouter = express.Router();
privateClubsApiRouter.use(assignUser)
privateClubsApiRouter.use(authenticateRole(UserRole.Admin))

privateClubsApiRouter.get('/',
    async (req: Request, res: Response) => {
        const results = await clubController.getAll()
        return res.status(200).send(results)
    })

 privateClubsApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await clubController.getById(id)
        return res.status(200).send(result)
    })

    privateClubsApiRouter.delete('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)

        const result = await clubController.deleteById(id)
        return res.status(204).send({
            success: result
        })
    })

publicClubsApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const shows = await showController.getAll()
        const groupedShows = groupByPropertyCount(shows, "clubId")

        const topFive = Object.keys(groupedShows)
        .map((clubId: string) => {
            const showArray = groupedShows[clubId]
            const size = showArray.length
            return {
                clubId,
                size
            }
        })
        .sort((a, b) => a.size - b.size)
        .slice(0, 5)

        const topFiveIds = topFive.map((object: any) => Number(object.clubId))

        return clubController.getAllClubsById(topFiveIds).then((clubs: ClubInterface[]) => {
            const clubsResponse = clubs.map((club: ClubInterface) => {
                return {
                    id: club.id,
                    name: club.name,
                    url: club.baseUrl,
                    count: groupedShows[club.id].length
                }
            })

            return res.status(200).send(clubsResponse)
        })
    })