import * as clubController from "../controllers/club/index.js"
import express, { Request, Response} from "express"; 
import { CreateClubDTO } from "../dto/club.dto.js";
import { readJsonFile } from "../../util/fileSystemUtil.js";
import { JSON_KEYS } from "../../constants/objects.js";

export const clubsApiRouter = express.Router();

const clubs = readJsonFile(process.env.CLUBS_FILE ?? "src/clubs.json")
.flatMap((json: any) => {
    return json[JSON_KEYS.clubs]
    .map((club: any) => {
        return {
            ...club,
            scraping_config: json[JSON_KEYS.scrapingConfig],
        }
    })
})

clubsApiRouter.get('/', async (req: Request, res: Response) => {
    const results = await clubController.getAll()
    return res.status(200).send(results)
})

clubsApiRouter.get('/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)
    const result = await clubController.getById(id)
    return res.status(200).send(result)
})

clubsApiRouter.delete('/:id', async (req: Request, res: Response) => {
    const id = Number(req.params.id)

    const result = await clubController.deleteById(id)
    return res.status(204).send({
        success: result
    })
})

clubsApiRouter.post('/', async (req: Request, res: Response) => {
    const payload: CreateClubDTO = req.body
    const result = await clubController.create(payload)
    return res.status(200).send(result)
})

clubsApiRouter.post('/all', async (req: Request, res: Response) => {
    await clubController.createAll(clubs)
    return res.status(200).send({
        success: true
    })
})