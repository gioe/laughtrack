import * as showController from '../../controllers/show/index.js'
import * as showComedianController from '../../controllers/showComedian/index.js'

import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { groupByPropertyCount } from '../../util/groupUtil.js';
import { GetSearchResultsOutput } from '../../dto/comedian.dto.js';

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
        
        const shows = await showController.getSearchResults(req.body);
        console.log(shows)
        const groupedShowRecord = groupByPropertyCount(shows, 'comedian_name')

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
            .map(({comedianName}) => {
                const showArray = groupedShowRecord[comedianName]
                const firstEntry = showArray[0];
                return {
                    comedians: {
                        id: firstEntry.comedian_id,
                        name: comedianName,
                        instagram: firstEntry.instagram,
                        shows: showArray.map((value: GetSearchResultsOutput) => {
                            return {
                                id: value.show_id,
                                dateTime: value.date_time,
                                ticketLink: value.ticket_link,
                                club: {
                                    name: value.club_name,
                                    address: value.address,
                                    url: value.base_url
                                },
                            }
                        })
                    },
                }
            })
            
        return res.status(200).send({
            total: shows.length,
            results: topTenSearchResults,
        })
    })