const LETTER_OR_DIGIT = /[A-Za-z0-9\u00C0-\uFFFF]/;

function firstLetter(word: string): string {
    for (let i = 0; i < word.length; i++) {
        const ch = word[i];
        if (LETTER_OR_DIGIT.test(ch)) return ch.toUpperCase();
    }
    return "";
}

export function getInitials(name: string | null | undefined): string {
    if (!name) return "";
    const words = name.trim().split(/\s+/).filter(Boolean);
    if (words.length === 0) return "";
    if (words.length === 1) {
        const chars: string[] = [];
        for (let i = 0; i < words[0].length && chars.length < 2; i++) {
            const ch = words[0][i];
            if (LETTER_OR_DIGIT.test(ch)) chars.push(ch.toUpperCase());
        }
        return chars.join("");
    }
    return firstLetter(words[0]) + firstLetter(words[words.length - 1]);
}
