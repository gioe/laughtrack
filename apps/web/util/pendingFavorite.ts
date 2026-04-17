const STORAGE_KEY = "laughtrack:pendingFavorite";

export interface PendingFavorite {
    entityId: string;
    setFavorite: boolean;
}

function isPendingFavorite(value: unknown): value is PendingFavorite {
    return (
        typeof value === "object" &&
        value !== null &&
        typeof (value as PendingFavorite).entityId === "string" &&
        (value as PendingFavorite).entityId.length > 0 &&
        typeof (value as PendingFavorite).setFavorite === "boolean"
    );
}

export const pendingFavorite = {
    set(value: PendingFavorite): void {
        if (typeof window === "undefined") return;
        try {
            window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
        } catch {
            // sessionStorage unavailable (private mode quota, etc.) — silently skip
        }
    },

    get(): PendingFavorite | null {
        if (typeof window === "undefined") return null;
        try {
            const raw = window.sessionStorage.getItem(STORAGE_KEY);
            if (!raw) return null;
            const parsed: unknown = JSON.parse(raw);
            return isPendingFavorite(parsed) ? parsed : null;
        } catch {
            return null;
        }
    },

    clear(): void {
        if (typeof window === "undefined") return;
        try {
            window.sessionStorage.removeItem(STORAGE_KEY);
        } catch {
            // ignore
        }
    },

    consume(entityId: string): PendingFavorite | null {
        const current = this.get();
        if (current && current.entityId === entityId) {
            this.clear();
            return current;
        }
        return null;
    },
};
