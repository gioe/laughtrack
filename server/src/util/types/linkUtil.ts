import { LINKS } from "../../constants/links.js"

export const validLink = (link: string): boolean => {
    return !LINKS.badLinks.includes(link) &&
     !link.includes("http") && 
     !link.includes("https")

}
