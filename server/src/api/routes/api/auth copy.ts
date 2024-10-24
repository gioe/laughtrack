import * as userController from '../../controllers/user/index.js'

import bcrypt from "bcrypt";
import bodyParser from "body-parser";
import express, { Request, Response } from "express";
import { UserInterface } from "../../../common/models/interfaces/user.interface.js";
import { generateToken, verifyToken } from '../../../common/util/domainModels/token/index.js';

export const authApiRouter = express.Router();
var urlencodedParser = bodyParser.urlencoded({ extended: false })

authApiRouter.post('/register',
    urlencodedParser,
    async (req: Request, res: Response) => {

        const { email, password } = req.body
        const emailString = email as string;
        const passwordString = password as string;

        const userExists = await userController.checkIfUserExists(emailString)

        if (userExists && emailString !== "" && passwordString !== "") {
            return res.status(200).json({
                error: "The user already exists",
            });
        }

        return bcrypt.hash(passwordString, 10)
            .then((hash: string) => userController.register(emailString, hash))
            .then((response: any) => userController.getUserById(response.id))
            .then((user: UserInterface | null) => {
                if (user) {
                    return res.status(200).json({ id: user.id })
                }
                throw new Error("User doesn't exist")
            })
            .catch((error: any) => res.status(500).json({ error }))

    });

authApiRouter.post('/login',
    urlencodedParser,
    async (req: Request, res: Response) => {
        const { email, password } = req.body

        const emailString = email as string;

        const userExists = await userController.checkIfUserExists(emailString)

        if (!userExists) {
            return res.status(400).json({ error: "User doesn't exist." });
        }

        const user = await userController.getUserByEmail(emailString)

        if (!user) {
            return res.status(400).json({ error: "User doesn't exist." });
        }

        const passwordString = password as string;

        return bcrypt.compare(passwordString, user.password ?? "")
            .then((result: boolean) => {
                if (result) return userController.getUserByEmail(emailString)
                else throw new Error("Passwords don't match")
            })
            .then((user: UserInterface | null) => {
                if (user) {
                    return loginUser(res, user)
                }
                throw new Error("User doesn't exist")
            })
            .catch((error: any) => res.status(500).json({ error }))
    });

authApiRouter.post('/refresh',
    urlencodedParser,
    async (req: Request, res: Response) => {
        const authHeader = req.headers['authorization'];
        const refreshToken = authHeader && authHeader.split(' ')[1];  // Bear

        if (!refreshToken) return res.status(401).send("refresh token not provided");

        try {
            const payload = verifyToken(refreshToken);
            const accessToken = generateToken({ id: payload.id, email: payload.email }, "access");
            return res.status(200).send({ accessToken });
        } catch (err) {
            return res.status(403).send(err);
        }

    });

const loginUser = (res: Response, user: UserInterface) => {
    const accessToken = generateToken({ id: user.id, email: user.email }, 'access');
    const refreshToken = generateToken({ id: user.id, email: user.email }, 'refresh');

    return res.status(200).json({
        success: true,
        data: {
            user: {
                id: user.id,
                email: user.email,
                role: user.role
            },
            accessToken,
            refreshToken
        }
    })
}
