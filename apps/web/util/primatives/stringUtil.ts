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

const HTML_ENTITY_MAP: Record<string, string> = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&apos;": "'",
    "&nbsp;": " ",
    "&hellip;": "…",
    "&mdash;": "—",
    "&ndash;": "–",
    "&rsquo;": "’",
    "&lsquo;": "‘",
    "&rdquo;": "”",
    "&ldquo;": "“",
};

export const stripHtmlTags = (input: string): string => {
    const blockBreaks = input
        .replace(/<\s*br\s*\/?\s*>/gi, "\n")
        .replace(/<\s*\/\s*(p|div|li|h[1-6])\s*>/gi, "\n\n")
        .replace(/<\s*li\b[^>]*>/gi, "• ");
    const stripped = blockBreaks.replace(/<[^>]+>/g, "");
    const decoded = stripped.replace(/&[a-z#0-9]+;/gi, (match) => {
        const named = HTML_ENTITY_MAP[match.toLowerCase()];
        if (named) return named;
        const numeric = /^&#(\d+);$/.exec(match);
        if (numeric) return String.fromCodePoint(Number(numeric[1]));
        const hex = /^&#x([0-9a-f]+);$/i.exec(match);
        if (hex) return String.fromCodePoint(parseInt(hex[1], 16));
        return match;
    });
    return decoded.replace(/\n{3,}/g, "\n\n").trim();
};
