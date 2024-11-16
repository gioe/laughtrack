import { HeaderKey } from "../../objects/enum"

export const getDefaultHeaderValue = (key: HeaderKey) => {
    switch (key) {
        case HeaderKey.Path: return "/home"
    }

}
