export const removeNonNumbers = (inputString: string) => {
    return inputString.replace(/\D/g,'');
}


export const removeSubstrings = (inputString: string, replacements?: string[]) => {
    var mutatedString = inputString;
    for (const replacement of replacements ?? []) {
        mutatedString = mutatedString.replaceAll(replacement, "")
    }
    return removeBadWhiteSpace(mutatedString)
}

export const removeBadWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.trimEnd().trimStart()
} 

export const stringIsAValidUrl = (string: string): boolean => {
    var urlPattern = new RegExp('^(https?:\\/\\/)?'+ // validate protocol
	    '((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|'+ // validate domain name
	    '((\\d{1,3}\\.){3}\\d{1,3}))'+ // validate OR ip (v4) address
	    '(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*'+ // validate port and path
	    '(\\?[;&a-z\\d%_.~+=-]*)?'+ // validate query string
	    '(\\#[-a-z\\d_]*)?$','i'); // validate fragment locator
	  return !!urlPattern.test(string);
}

export const stringIsAValidDate = (string: string): boolean => {
    if (string == undefined) return false
    var date = Date.parse(string);
    return !isNaN(date) 
}

export const generateValidUrls = (url: string, hrefs: string[]) => {
    return hrefs.map((link: string) => generateValidUrl(url, link))
	.filter((url: string) => stringIsAValidUrl(url))
	.filter((url: string) => !url.includes('fcomedyclub'))
}

export const generateValidUrl = (url: string, href: string) => {
    return toUrl(url, href)
}

export const toUrl = (url: string, href: string): string => {
	if (pathIsCompleteUrl(href)) return href

    const pageOrigin = new URL(url).origin;
	return `${pageOrigin}${href}`

}

export const pathIsCompleteUrl = (href: string) => {
	try {
		const url = new URL(href);
		return true
	 } catch {
		return false
	 }
}
