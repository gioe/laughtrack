export const removeAllWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.replaceAll(" ", "_")
}

export const removeLeadingWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.trimStart()
}

export const removeTrailingWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.trimEnd()
}

export const makeAlphaNumeric = (inputStrings: string[]) => {
    return inputStrings.map((regexString: string) => regexString.replace(/[^0-9a-z]/gi, ''))
}

export const removeSubstrings = (inputString: string, replacements: string[]) => {
    var mutatedString = inputString;
    for (const provider of replacements) {
        mutatedString = mutatedString.replaceAll(provider, "")
    }
    return mutatedString
}

export const removeBadWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.trimEnd().trimStart()
} 