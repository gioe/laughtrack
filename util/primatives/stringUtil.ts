export const removeNonNumbers = (inputString: string) => {
    return inputString.replace(/\D/g, "");
};

export const removeSubstrings = (
    inputString: string,
    replacements?: string[],
) => {
    let mutatedString = inputString;
    for (const replacement of replacements ?? []) {
        mutatedString = mutatedString.replaceAll(replacement, "");
    }
    return removeBadWhiteSpace(mutatedString);
};

export const removeBadWhiteSpace = (whiteSpaceString: string) => {
    return whiteSpaceString.trimEnd().trimStart();
};


export const stringIsAValidDate = (string: string): boolean => {
    if (string == undefined) return false;
    const date = Date.parse(string);
    return !isNaN(date);
};
