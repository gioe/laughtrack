"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { NATIVE_AUTH_DEEP_LINK } from "@/lib/auth/nativeDeepLink";
import { Button } from "@/ui/components/ui/button";
import { Form } from "../../ui/form";
import { FormInput } from "../components/input";

const reviewAccessSchema = z.object({
    email: z.string().email("Please enter the supplied review email"),
    password: z
        .string()
        .min(1, "Please enter the supplied review password")
        .max(256, "Password is too long"),
});

type ReviewAccessValues = z.infer<typeof reviewAccessSchema>;

type ReviewTokenResponse = {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
};

interface ReviewAccessFormProps {
    nativeCallbackUrl: string;
}

export default function ReviewAccessForm({
    nativeCallbackUrl,
}: ReviewAccessFormProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const form = useForm<ReviewAccessValues>({
        resolver: zodResolver(reviewAccessSchema),
        defaultValues: { email: "", password: "" },
        mode: "onBlur",
    });

    const handleSubmit = async (values: ReviewAccessValues) => {
        try {
            const response = await fetch("/api/v1/auth/review-token", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(values),
                cache: "no-store",
            });

            if (!response.ok) {
                toast.error("The review email or password is incorrect.");
                return;
            }

            const tokens = (await response.json()) as ReviewTokenResponse;
            window.location.assign(
                buildReviewCallbackUrl(nativeCallbackUrl, tokens),
            );
        } catch {
            toast.error("Review sign-in failed. Please try again.");
        }
    };

    if (!isExpanded) {
        return (
            <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => setIsExpanded(true)}
            >
                App review access
            </Button>
        );
    }

    const isSubmitting = form.formState.isSubmitting;

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} noValidate>
                <div className="space-y-4 rounded-lg border border-subtle p-4">
                    <p className="text-sm text-muted-foreground font-dmSans">
                        For Apple and Google review teams using the credentials
                        supplied with this submission.
                    </p>
                    <FormInput
                        isLoading={isSubmitting}
                        form={form}
                        name="email"
                        label="Review email"
                        placeholder="review@example.com"
                        type="email"
                    />
                    <FormInput
                        isLoading={isSubmitting}
                        form={form}
                        name="password"
                        label="Review password"
                        placeholder="Password"
                        type="password"
                    />
                    <Button
                        type="submit"
                        variant="roundedShimmer"
                        disabled={isSubmitting}
                        className="w-full gap-2"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Signing in…</span>
                            </>
                        ) : (
                            "Sign in to review account"
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    );
}

export function buildReviewCallbackUrl(
    nativeCallbackUrl: string,
    tokens: ReviewTokenResponse,
): string {
    const nativeRequest = new URL(nativeCallbackUrl);
    const state = nativeRequest.searchParams.get("state");
    if (!state) throw new Error("Native review callback is missing state");

    const callback = new URL(NATIVE_AUTH_DEEP_LINK);
    callback.searchParams.set("provider", "email");
    callback.searchParams.set("state", state);
    callback.searchParams.set("accessToken", tokens.accessToken);
    callback.searchParams.set("refreshToken", tokens.refreshToken);
    callback.searchParams.set("expiresIn", String(tokens.expiresIn));
    return callback.toString();
}
