export const combineWebsite = (base: string, ticketLinks: string[]) => {
    if (ticketLinks.length > 0) {
        return `${base}${ticketLinks[0]}`
    }
    return ""
}