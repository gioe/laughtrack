/* eslint-disable @typescript-eslint/no-explicit-any */
import jwt from "jsonwebtoken";
import { AuthToken } from "../../objects/interface";

const secret = process.env.SECRET_KEY;
if (!secret) throw new Error("SECRET_KEY environment variable is not set");

export const generateToken = (payload: any, type: string) => {
    if (type === "access") {
        return jwt.sign(payload, secret, {
            expiresIn: "24h",
        });
    } else if (type === "refresh") {
        return jwt.sign(payload, secret, {
            expiresIn: "30d",
        });
    }
};

export const verifyToken = (token: string) => {
    return jwt.verify(token, secret) as AuthToken;
};
