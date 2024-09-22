import * as showController from '../../controllers/show/index.js'
import * as showComedianController from '../../controllers/showComedian/index.js'

import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { groupByPropertyCount } from '../../util/groupUtil.js';
import { GetShowComedianDetailsOutput } from '../../dto/comedian.dto.js';

export const showApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items

showApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send(result)
    })


showApiRouter.post('/search', urlencodedParser,
    async (req: Request, res: Response) => {        
        const shows = await showController.getAllShowsBetweenDatesAtLocation(req.body)
        const comedians = await showComedianController.getAllComediansOnShows(shows.map(show => show.show_id))

        const groupedShowRecord = groupByPropertyCount(comedians, 'comedian_name')

        const topTenSearchResults = Object.keys(groupedShowRecord)
            .map((comedianName: string) => {
                const showArray = groupedShowRecord[comedianName]
                const count = showArray.length
                return {
                    comedianName,
                    count
                }
            })
            .sort((a, b) => b.count - a.count)
            .slice(0, 10)
            .map((object: any) => {
                return {
                    id: groupedShowRecord[object.comedianName][0].comedian_id,
                    name: object.comedianName,
                    instagram: groupedShowRecord[object.comedianName][0].instagram,
                    shows: groupedShowRecord[object.comedianName].map((value: GetShowComedianDetailsOutput) => {
                        return {
                            id: value.show_id,
                            dateTime: value.date_time,
                            ticketLink: value.ticket_link,
                            club: {
                                name: value.club_name,
                                address: value.address,
                                url: value.base_url,
                                latitude: value.latitude,
                                longitude: value.longitude
                            },
                        }
                    })
                }
            })
            
        return res.status(200).send(topTenSearchResults)
    })