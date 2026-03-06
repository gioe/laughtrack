"use client";

import React, { Component, ReactNode } from "react";
import * as Sentry from "@sentry/nextjs";
import ErrorPage from "@/ui/components/errorPage";

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    retryKey: number;
}

class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, retryKey: 0 };
    }

    static getDerivedStateFromError() {
        return { hasError: true };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        Sentry.captureException(error, {
            extra: { componentStack: info.componentStack },
        });
        if (process.env.NODE_ENV !== "production") {
            console.error("ErrorBoundary caught an error:", error, info);
        }
    }

    render() {
        const { hasError, retryKey } = this.state;

        if (hasError) {
            const reset = () =>
                this.setState((prev) => ({
                    hasError: false,
                    retryKey: prev.retryKey + 1,
                }));

            if (this.props.fallback) {
                return this.props.fallback;
            }
            return (
                <ErrorPage
                    title="Something went wrong"
                    description="An unexpected error occurred. Please try again."
                    reset={reset}
                />
            );
        }

        return (
            <React.Fragment key={retryKey}>
                {this.props.children}
            </React.Fragment>
        );
    }
}

export default ErrorBoundary;
