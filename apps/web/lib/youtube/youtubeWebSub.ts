export interface YouTubeWebSubEntry {
    videoId: string | null;
    channelId: string | null;
    title: string | null;
    link: string | null;
    publishedAt: string | null;
    updatedAt: string | null;
}

export function parseYouTubeWebSubFeed(xml: string): YouTubeWebSubEntry[] {
    return Array.from(xml.matchAll(/<entry\b[^>]*>([\s\S]*?)<\/entry>/gi), (match) => {
        const entryXml = match[1] ?? "";

        return {
            videoId: getTagText(entryXml, "yt:videoId"),
            channelId: getTagText(entryXml, "yt:channelId"),
            title: getTagText(entryXml, "title"),
            link: getAlternateLink(entryXml),
            publishedAt: getTagText(entryXml, "published"),
            updatedAt: getTagText(entryXml, "updated"),
        };
    });
}

function getTagText(xml: string, tagName: string): string | null {
    const pattern = new RegExp(`<${escapeRegExp(tagName)}\\b[^>]*>([\\s\\S]*?)<\\/${escapeRegExp(tagName)}>`, "i");
    const value = pattern.exec(xml)?.[1];

    if (!value) {
        return null;
    }

    return decodeXmlValue(value.replace(/^<!\[CDATA\[([\s\S]*)\]\]>$/, "$1").trim());
}

function getAlternateLink(xml: string): string | null {
    for (const match of xml.matchAll(/<link\b([^>]*)>/gi)) {
        const attributes = match[1] ?? "";
        if (getAttribute(attributes, "rel") === "alternate") {
            return getAttribute(attributes, "href");
        }
    }

    return null;
}

function getAttribute(attributes: string, name: string): string | null {
    const pattern = new RegExp(`${escapeRegExp(name)}\\s*=\\s*("([^"]*)"|'([^']*)')`, "i");
    const match = pattern.exec(attributes);
    const value = match?.[2] ?? match?.[3];

    return value ? decodeXmlValue(value) : null;
}

function decodeXmlValue(value: string): string {
    return value.replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (entity, code: string) => {
        switch (code.toLowerCase()) {
            case "amp":
                return "&";
            case "lt":
                return "<";
            case "gt":
                return ">";
            case "quot":
                return '"';
            case "apos":
                return "'";
            default:
                if (code.toLowerCase().startsWith("#x")) {
                    return String.fromCodePoint(Number.parseInt(code.slice(2), 16));
                }
                if (code.startsWith("#")) {
                    return String.fromCodePoint(Number.parseInt(code.slice(1), 10));
                }
                return entity;
        }
    });
}

function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
