import * as clubController from "../../controllers/club/index.js"
import * as showController from "../../controllers/show/index.js"
import express, { Request, Response } from "express";
import { groupByPropertyCount } from "../../util/groupUtil.js";
import { ClubInterface } from "../../../common/interfaces/club.interface.js";

export const clubsApiRouter = express.Router();

clubsApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await clubController.getById(id)
        return res.status(200).send(result)
    })

clubsApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const shows = await showController.getAll()
        const groupedShows = groupByPropertyCount(shows, "clubId")

        const topFive = Object.keys(groupedShows)
            .map((clubId: string) => {
                const showArray = groupedShows[clubId]
                const count = showArray.length
                return {
                    clubId,
                    count
                }
            })
            .sort((a, b) => b.count - a.count)
            .slice(0, 5)

        const topFiveIds = topFive.map((object: any) => Number(object.clubId))

        const clubs = await clubController.getAllClubsById(topFiveIds)

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