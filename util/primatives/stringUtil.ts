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

export const stringIsAValidUrl = (string: string): boolean => {
    const urlPattern = new RegExp(
        "^(https?:\\/\\/)?" + // validate protocol
        "((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|" + // validate domain name
        "((\\d{1,3}\\.){3}\\d{1,3}))" + // validate OR ip (v4) address
        "(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*" + // validate port and path
        "(\\?[;&a-z\\d%_.~+=-]*)?" + // validate query string
        "(\\#[-a-z\\d_]*)?$",
        "i",
    ); // validate fragment locator
    return !!urlPattern.test(string);
};

export const stringIsAValidDate = (string: string): boolean => {
    if (string == undefined) return false;
    const date = Date.parse(string);
    return !isNaN(date);
};

export const capitalized = (inputString: string): string => {
    const newString = inputString
        .split(" ")
        .filter((word) => word !== "")
        .map((word) => {
            if (isAcronym(word)) return word
            return word[0].toUpperCase() + word.substring(1).toLowerCase()
        })
        .join(" ");
    console.log(`${inputString} in, ${newString} out`)
    return newString
};

const isAcronym = (word: string): boolean => {
    return word.includes('.')
}

export const removeNonAlphanumeric = (str: string): string => {
    return str.replace(/[^a-zA-Z0-9]/g, "");
};

export const isUpperCase = (inputString: string): boolean => {
    return inputString === inputString.toUpperCase();
}

export const isLowerCase = (inputString: string): boolean => {
    return inputString === inputString.toLowerCase();
}
