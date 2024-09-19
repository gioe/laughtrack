import express, { Request, Response } from "express";

import bcrypt from "bcrypt";
import * as userController from '../controllers/user/index.js'
import { GetUserDetailsOutput, RegisterUserOutput } from "../dto/user.dto.js";
import bodyParser from "body-parser";
import { generateToken, verifyToken } from "../util/tokenUtil.js";

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
            .then((response: RegisterUserOutput) => userController.getUserById(response.id))
            .then((user: GetUserDetailsOutput) => res.status(200).json({ id: user.id }))
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
        const passwordString = password as string;

        return bcrypt.compare(passwordString, user.password)
            .then((result: boolean) => {
                if (result) return userController.getUserByEmail(emailString)
                else throw new Error("Passwords don't match")
            })
            .then((user: GetUserDetailsOutput) => loginUser(res, user))
            .catch((error: any) => res.status(500).json({ error }))
    });

authApiRouter.post('/refresh',
    urlencodedParser,
    async (req: Request, res: Response) => {

        const { refreshToken, user } = req.body
        if (!refreshToken) return res.status(401).send("refresh token not provided");

        try {
            const payload = verifyToken(refreshToken);
            const accessToken = generateToken({ id: payload.id, email: payload.email }, "access");
            return res.status(200).send({ accessToken });
        } catch (err) {
            return res.status(403).send(err);
        }

    });

const loginUser = (res: Response, user: GetUserDetailsOutput) => {
    const accessToken = generateToken({ id: user.id, email: user.email }, 'access');
    const refreshToken = generateToken({ id: user.id, email: user.email }, 'refresh');

    return res.status(200).json({
        success: true,
        data: {
            user: {
                email: user.email,
                role: user.role
            },
            accessToken,
            refreshToken
        }
    })
}
