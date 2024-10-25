import * as showController from '../controllers/show/index.js'
import * as tagController from '../controllers/tag/index.js'
import * as lineupController from '../controllers/lineup/index.js'

import bodyParser from "body-parser";
import express, { Request, Response } from "express";
import { toCreateLineupItemDTOArray } from '../../common/util/domainModels/lineupItem/mapper.js';
import { toCreateShowTagDTOArray } from '../../common/util/domainModels/tag/mapper.js';

export const showApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

showApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {
        const id = Number(req.params.id)
        const result = await showController.getById(id)
        return res.status(200).send({
            entity: result
        })
    })


showApiRouter.get('/tags/all', urlencodedParser,
    async (req: Request, res: Response) => {
        const result = await tagController.getAllByType({
            type: 'show'
        })
        return res.status(200).send({
            tags: result
        })
    })

showApiRouter.put('/lineup', urlencodedParser,
    async (req: Request, res: Response) => {
        const { comedians, showId } = req.body
        const idArray = comedians.split(",")
        const comedianIds = idArray.map((value: string) => {
            return {
                id: value
            }
        })
        const input = toCreateLineupItemDTOArray(comedianIds, showId)
        await lineupController.addAll(input)
        return res.status(200).send({
            success: true
        })
    })

showApiRouter.put('/tag', urlencodedParser,
    async (req: Request, res: Response) => {
        const { tags, showId } = req.body
        const idArray = tags.split(",")
        const tagIds = idArray.map((value: string) => {
            return {
                id: value
            }
        })
        const input = toCreateShowTagDTOArray(tagIds, showId)
        
        await tagController.addShowTags(input)
        return res.status(200).send({
            success: true
        })
    })
