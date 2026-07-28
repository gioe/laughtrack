"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import useLoginModal from "./useLoginModal";

const LOAD_ERROR = "Unable to check whether this show is saved.";
const MUTATION_ERROR = "Unable to update this saved show. Please try again.";

type SavedShowResponse = {
    data?: {
        isSaved?: unknown;
    };
    error?: unknown;
};

interface UseSavedShowReturn {
    isSaved: boolean;
    isAuthenticated: boolean;
    isLoading: boolean;
    isPending: boolean;
    error: string | null;
    announcement: string;
    toggleSavedShow: () => Promise<void>;
}

async function parseSavedShowResponse(
    response: Response,
    fallbackError: string,
): Promise<boolean> {
    const body = (await response
        .json()
        .catch(() => null)) as SavedShowResponse | null;

    if (!response.ok) {
        throw new Error(
            typeof body?.error === "string" ? body.error : fallbackError,
        );
    }

    if (typeof body?.data?.isSaved !== "boolean") {
        throw new Error(fallbackError);
    }

    return body.data.isSaved;
}

export function useSavedShow(showId: number): UseSavedShowReturn {
    const session = useSession();
    const loginModal = useLoginModal();
    const [isSaved, setIsSaved] = useState(false);
    const [isStateLoading, setIsStateLoading] = useState(true);
    const [isPending, setIsPending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [announcement, setAnnouncement] = useState("");
    const isAuthenticated = session.status === "authenticated";
    const isLoading = session.status === "loading" || isStateLoading;

    useEffect(() => {
        if (!isAuthenticated) {
            setIsSaved(false);
            setIsStateLoading(false);
            setError(null);
            setAnnouncement("");
            return;
        }

        const controller = new AbortController();
        setIsStateLoading(true);
        setError(null);
        setAnnouncement("");

        void fetch(`/api/v1/saved-shows/${showId}`, {
            method: "GET",
            signal: controller.signal,
        })
            .then((response) => parseSavedShowResponse(response, LOAD_ERROR))
            .then((saved) => {
                if (!controller.signal.aborted) setIsSaved(saved);
            })
            .catch((cause: unknown) => {
                if (controller.signal.aborted) return;
                setError(cause instanceof Error ? cause.message : LOAD_ERROR);
            })
            .finally(() => {
                if (!controller.signal.aborted) setIsStateLoading(false);
            });

        return () => controller.abort();
    }, [isAuthenticated, showId]);

    const toggleSavedShow = useCallback(async () => {
        if (!isAuthenticated) {
            loginModal.onOpen();
            return;
        }
        if (isLoading || isPending) return;

        const nextSaved = !isSaved;
        setIsPending(true);
        setError(null);
        setAnnouncement("");

        try {
            const response = await fetch(`/api/v1/saved-shows/${showId}`, {
                method: nextSaved ? "POST" : "DELETE",
            });
            const saved = await parseSavedShowResponse(
                response,
                MUTATION_ERROR,
            );
            if (saved !== nextSaved) throw new Error(MUTATION_ERROR);

            setIsSaved(saved);
            setAnnouncement(saved ? "Show saved." : "Saved show removed.");
        } catch (cause) {
            setError(cause instanceof Error ? cause.message : MUTATION_ERROR);
        } finally {
            setIsPending(false);
        }
    }, [isAuthenticated, isLoading, isPending, isSaved, loginModal, showId]);

    return {
        isSaved,
        isAuthenticated,
        isLoading,
        isPending,
        error,
        announcement,
        toggleSavedShow,
    };
}
