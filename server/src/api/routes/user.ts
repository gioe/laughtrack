import express, { Request, Response } from "express";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import * as userController from '../controllers/user/index.js'
import { GetUserDetailsOutput } from "../dto/user.dto.js";

export const userApiRouter = express.Router();

userApiRouter.post('/register', async (req: Request, res: Response) => {

    const userExists = await userController.checkIfUserExists(req.params.email)

    if (userExists) {
        return res.status(400).json({
            error: "Email already there, No need to register again.",
        });
    }

    const { email, password } = req.query;

    return bcrypt.hash(password as string, 10)
        .then((hash: string) => {
            return userController.register({
                email: email as string,
                password: hash
            })
        }).then((user: GetUserDetailsOutput) => {
            const token = jwt.sign({ email: user.email }, process.env.SECRET_KEY as string);
            return res.status(200).json({
                message: "User signed in!",
                token: token
            })
        })
});

userApiRouter.post('/login', async (req: Request, res: Response) => {
    const userExists = await userController.checkIfUserExists(req.params.email)

    if (!userExists) {
        return res.status(400).json({
            error: "User is not registered.",
        });
    }

    const user = await userController.getUserByEmail(req.params.email)

    return bcrypt.compare(req.params.password, user.password)
        .then((result: boolean) => {
            const token = jwt.sign({ email: user.email }, process.env.SECRET_KEY as string);
            return res.status(200).json({
                message: "User signed in!",
                token: token
            })
        })
        .catch((error: any) => res.status(500).json({ error: "Server error" }))
});

