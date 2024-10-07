import { UserInterface } from "../../api/interfaces/user.interface.ts";
import { UserModel } from "../../src/user/user.model";

declare global{
    namespace Express {
        interface Request {
            currentUser?: UserInterface
        }
    }
}
