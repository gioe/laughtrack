import * as showController from '../../controllers/show/index.js'
import * as clubController from '../../controllers/club/index.js'
import * as showComedianController from '../../controllers/showComedian/index.js'

import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { ClubInterface } from '../../../common/interfaces/club.interface.js';
import { ShowInterface } from '../../../common/interfaces/show.interface.js';
import { groupByPropertyCount } from '../../util/groupUtil.js';
import { GetFilteredShowsRequest } from '../../dto/show.dto.js';

export const showsApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

// POST items

showsApiRouter.get('/:id',
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send(result)
    })


    showsApiRouter.post('/search', urlencodedParser,
    async (req: Request, res: Response) => {
        
        const shows = await showController.getAllShowsBetweenDatesAtLocation(req.body)
        const comedians = await showComedianController.getAllComediansOnShows(shows.map(show => show.show_id)) 

        const groupedShowRecord = groupByPropertyCount(comedians, 'comedian_name')

        const topTen = Object.keys(groupedShowRecord)
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
                comedian: object.comedianName, 
                schedule: groupedShowRecord[object.comedianName].map((value: any) => {
                    return {
                        dateTime: value.date_time,
                        ticketLink: value.ticket_link,
                        clubName: value.club_name,
                        address: value.address,
                        url: value.base_url
                    }
                })
            }
        })

        console.log(topTen)

        return res.status(200).send({data: topTen})
    })