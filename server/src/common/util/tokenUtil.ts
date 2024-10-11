import jwt from "jsonwebtoken";
import { AuthToken } from "../models/interfaces/token.interface.js";

const secret = process.env.SECRET_KEY as string

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
