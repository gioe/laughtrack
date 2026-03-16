"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import LaughtrackLogin from "@/ui/pages/login";
import FullScreenModal from "../fullscreen";
import { useLoginModal } from "@/hooks";

const AUTH_ERROR_MESSAGES: Record<string, string> = {
    OAuthSignin: "Could not start sign-in. Please try again.",
    OAuthCallback: "Sign-in was cancelled or failed. Please try again.",
    OAuthCreateAccount: "Could not create your account. Please try again.",
    Callback: "Sign-in failed. Please try again.",
    Default: "Sign-in failed. Please try again.",
};

const LoginModal = () => {
    const router = useRouter();
    const onOpen = useLoginModal((s) => s.onOpen);
    const onClose = useLoginModal((s) => s.onClose);
    const isOpen = useLoginModal((s) => s.isOpen);
    const searchParams = useSearchParams();

    useEffect(() => {
        const error = searchParams.get("error");
        if (error) {
            const message =
                AUTH_ERROR_MESSAGES[error] ?? AUTH_ERROR_MESSAGES.Default;
            onOpen();
            toast.error(message);
            // Remove the error param from the URL so it doesn't re-trigger
            const url = new URL(window.location.href);
            url.searchParams.delete("error");
            router.replace(url.pathname + url.search, { scroll: false });
        }
    }, [searchParams, onOpen, router]);

    const onSubmit = () => {
        router.refresh();
        onClose();
    };

    return (
        <FullScreenModal isOpen={isOpen} onClose={onClose}>
            <LaughtrackLogin handleSubmit={onSubmit} />
        </FullScreenModal>
    );
};

export default LoginModal;
