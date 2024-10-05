export const removeAllWhiteSpace = (whiteSpaceString: string): string => {
    
    var newString = whiteSpaceString
    for (var index = 0; index < whiteSpaceString.length; index++) {
        if (whiteSpaceString.charCodeAt(index) == 32) {
            newString = whiteSpaceString.substring(0, index - 1) + whiteSpaceString.substring(index, whiteSpaceString.length);
        }
    }

    return newString;
}

export const removeLeadingWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.trimStart()
}

export const removeTrailingWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.trimEnd()
}

export const makeAlphaNumeric = (inputString: string) => {
    return inputString.replace(/[^0-9a-z]/gi, '')
}

export const removeNonNumbers = (inputString: string) => {
    return inputString.replace(/\D/g,'');
}

export const replaceSubstrings = (inputString: string, targets: string[], replacement: string) => {
    var mutatedString = inputString;

    if (targets === undefined) {
        return mutatedString
    }
    
    for (const target of targets) {
        mutatedString = mutatedString.replaceAll(target, replacement)
    }
    
    return mutatedString
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