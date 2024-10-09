import * as comedianController from "../../controllers/comedian/index.js"
import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import { authenticateRole } from "../../middleware/authenticateRole.middleware.js";
import { UserRole } from "../../../common/@types/UserRole.js";
import { assignUser } from "../../middleware/assignUser.middleware.js";
import { ComedianInterface } from "../../../common/interfaces/client/comedian.interface.js";
import { generatePopularityScore } from "../../../common/util/scoringUtil.js";

export const comedianApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

comedianApiRouter.post('/favorite/all',
    assignUser,
    authenticateRole([UserRole.Admin, UserRole.User]),
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;
        const { page, pageSize, query } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        // Calculate the start and end indexes for the requested page
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;
        const comedians = await comedianController.getAllFavorites(req.currentUser.id)
        const paginatedComedians = comedians.slice(startIndex, endIndex);
        const totalPages = Math.ceil(comedians.length / pageSizeInt);

        return res.status(200).send({
            comedians: paginatedComedians,
            totalPages
        })

    })

comedianApiRouter.post('/addToFavorites/:id',
    assignUser,
    authenticateRole([UserRole.Admin, UserRole.User]),
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;
        const { isFavorite } = req.body;
        const idNumber = Number(id)

        if (idNumber == 0) return res.status(400).json({ error: "Comedian doesn't exist." });

        const result = await comedianController.favoriteComedian({
            comedian_id: idNumber,
            user_id: req.currentUser.id,
            is_favorite: isFavorite == "1" ? true : false
        })

        return res.status(200).send(result)
        
    })

comedianApiRouter.get('/:id', urlencodedParser,
    async (req: Request, res: Response) => {
        const { id } = req.params;

        const page = req.header("page");
        const pageSize = req.header("pageSize");
        const sort = req.header("sort")

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);
        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        const decodedName = decodeURI(id)

        const result = await comedianController.getByName(decodedName, sort)
        const dates = result?.dates ?? []

        const paginatedDates = dates.slice(startIndex, endIndex);
        const totalPages = Math.ceil(dates.length / pageSizeInt);

        return res.status(200).send({
            entity: {
                ...result,
                dates: paginatedDates
            },
            totalPages: isNaN(totalPages) ? 0 : totalPages
        })
    })

comedianApiRouter.post('/trending',
    async (req: Request, res: Response) => {
        const trendingComedians = await comedianController.getTrendingComedians()
        return res.status(200).send(trendingComedians)
    })

comedianApiRouter.post('/all',
    assignUser,
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { page, pageSize, query } = req.body;

        const pageInt = parseInt(page as string);
        const pageSizeInt = parseInt(pageSize as string);

        const startIndex = (pageInt - 1) * pageSizeInt;
        const endIndex = pageInt * pageSizeInt;

        var comedians: ComedianInterface[] = [];

        if (req.currentUser == undefined) {
            comedians = await comedianController.getAllComedians(query)
        } else {
            comedians = await comedianController.getAllComediansWithFavorites(req.currentUser.id, query)
        }

        const paginatedComedians = comedians.slice(startIndex, endIndex);
        const totalPages = Math.ceil(comedians.length / pageSizeInt);

        return res.status(200).send({
            comedians: paginatedComedians,
            totalPages,
            totalComedians: comedians.length
        })
    })

    comedianApiRouter.put('/social',
        assignUser,
        urlencodedParser,
        async (req: Request, res: Response) => {
            const {instagramAccount, youtubeAccount, youtubeFollowers, instagramFollowers, tiktokAccount, tiktokFollowers, website, id } = req.body;
            const instagramFollowerInt = parseInt(instagramFollowers as string)
            const tiktokFollowerInt = parseInt(tiktokFollowers as string)
            const youtubeFollowerInt = parseInt(youtubeFollowers as string)
            const instagramFollowerCount =  !isNaN(instagramFollowerInt) ? instagramFollowerInt : 0;
            const tiktokFollowerCount = !isNaN(tiktokFollowerInt) ? tiktokFollowerInt : 0;
            const youtubeFollowerCount = !isNaN(youtubeFollowerInt) ? youtubeFollowerInt : 0;


            const idNumber = parseInt(id as string)

            const response = await comedianController.updateSocialData({
                instagram_account: instagramAccount,
                tiktok_account: tiktokAccount,
                youtube_account: youtubeAccount,
                website: website,
                instagram_followers: instagramFollowerCount, 
                tiktok_followers:  tiktokFollowerCount,
                youtube_followers: youtubeFollowerCount,
                popularity_score: generatePopularityScore({
                    id: idNumber,
                    instagram_followers: instagramFollowerCount,
                    tiktok_followers:  tiktokFollowerCount,
                    youtube_followers:  youtubeFollowerCount
                }),
                id: idNumber,
            })
    
            return res.status(200).send(response)
        })

        
