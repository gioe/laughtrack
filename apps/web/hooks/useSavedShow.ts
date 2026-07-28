"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
    isStateKnown: boolean;
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
    const [isStateKnown, setIsStateKnown] = useState(false);
    const [isStateLoading, setIsStateLoading] = useState(true);
    const [isPending, setIsPending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [announcement, setAnnouncement] = useState("");
    const requestGenerationRef = useRef(0);
    const isAuthenticated = session.status === "authenticated";
    const isLoading = session.status === "loading" || isStateLoading;

    useEffect(() => {
        const requestGeneration = ++requestGenerationRef.current;
        setIsSaved(false);
        setIsStateKnown(false);
        setIsPending(false);
        setError(null);
        setAnnouncement("");

        if (!isAuthenticated) {
            setIsStateLoading(false);
            return () => {
                if (requestGenerationRef.current === requestGeneration) {
                    requestGenerationRef.current += 1;
                }
            };
        }

        const controller = new AbortController();
        setIsStateLoading(true);

        void fetch(`/api/v1/saved-shows/${showId}`, {
            method: "GET",
            signal: controller.signal,
        })
            .then((response) => parseSavedShowResponse(response, LOAD_ERROR))
            .then((saved) => {
                if (
                    !controller.signal.aborted &&
                    requestGenerationRef.current === requestGeneration
                ) {
                    setIsSaved(saved);
                    setIsStateKnown(true);
                }
            })
            .catch((cause: unknown) => {
                if (
                    controller.signal.aborted ||
                    requestGenerationRef.current !== requestGeneration
                ) {
                    return;
                }
                setError(cause instanceof Error ? cause.message : LOAD_ERROR);
            })
            .finally(() => {
                if (
                    !controller.signal.aborted &&
                    requestGenerationRef.current === requestGeneration
                ) {
                    setIsStateLoading(false);
                }
            });

        return () => {
            controller.abort();
            if (requestGenerationRef.current === requestGeneration) {
                requestGenerationRef.current += 1;
            }
        };
    }, [isAuthenticated, showId]);

    const toggleSavedShow = useCallback(async () => {
        if (!isAuthenticated) {
            loginModal.onOpen();
            return;
        }
        if (!isStateKnown || isLoading || isPending) return;

        const nextSaved = !isSaved;
        const requestGeneration = requestGenerationRef.current;
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
            if (requestGenerationRef.current !== requestGeneration) return;

            setIsSaved(saved);
            setAnnouncement(saved ? "Show saved." : "Saved show removed.");
        } catch (cause) {
            if (requestGenerationRef.current !== requestGeneration) return;
            setError(cause instanceof Error ? cause.message : MUTATION_ERROR);
        } finally {
            if (requestGenerationRef.current === requestGeneration) {
                setIsPending(false);
            }
        }
    }, [
        isAuthenticated,
        isLoading,
        isPending,
        isSaved,
        isStateKnown,
        loginModal,
        showId,
    ]);

    return {
        isSaved,
        isStateKnown,
        isAuthenticated,
        isLoading,
        isPending,
        error,
        announcement,
        toggleSavedShow,
    };
}
