import express, { Request, Response } from "express";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import * as userController from '../controllers/user/index.js'
import { GetUserDetailsOutput, RegisterUserOutput } from "../dto/user.dto.js";

export const userApiRouter = express.Router();

userApiRouter.post('/register',
     async (req: Request, res: Response) => {

    const userExists = await userController.checkIfUserExists(req.params.email)

    if (userExists) {
        return res.status(400).json({
            error: "Email already there, No need to register again.",
        });
    }

    const { email, password } = req.query
    
    const emailString = email as string;
    const passwordString = password as string;

    return bcrypt.hash(passwordString, 10)
        .then((hash: string) => userController.register(emailString, hash))
        .then((response: RegisterUserOutput) => userController.getUserById(response.id))
        .then((user: GetUserDetailsOutput) => loginUser(res, user))
        .catch((error: any) => res.status(500).json({ error }))
});

userApiRouter.post('/login', 
    async (req: Request, res: Response) => {
    const { email, password } = req.query
    
    const emailString = email as string;
    const passwordString = password as string;

    const userExists = await userController.checkIfUserExists(emailString)

    if (!userExists) {
        return res.status(400).json({
            error: "User is not registered.",
        });
    }

    const user = await userController.getUserByEmail(emailString)

    return bcrypt.compare(passwordString, user.password)
        .then((result: boolean) => { 
            if (result) return userController.getUserByEmail(emailString)
            else throw new Error("Passwords don't match")
        })
        .then((user: GetUserDetailsOutput) => loginUser(res, user))
        .catch((error: any) => res.status(500).json({ error }))
});

const loginUser = (res: Response, user: GetUserDetailsOutput) => {
    const token = jwt.sign({ id: user.id, email: user.email }, process.env.SECRET_KEY as string);
    return res.status(200).json({
        success: true,
        data: {
            userId: user.id,
            email: user.email,
            token: token
        }
    })
}
