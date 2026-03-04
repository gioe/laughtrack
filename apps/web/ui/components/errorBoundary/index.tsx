'use client';

import React, { Component, ReactNode } from 'react';
import Link from 'next/link';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
}

class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(): State {
        return { hasError: true };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, info);
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }
            return (
                <div className="min-h-[400px] flex flex-col items-center justify-center gap-6 bg-coconut-cream px-4 text-center">
                    <h1 className="text-3xl font-bold text-gray-800">Something went wrong</h1>
                    <p className="text-gray-500 max-w-md">An unexpected error occurred. Please try again.</p>
                    <div className="flex gap-4">
                        <button
                            onClick={() => this.setState({ hasError: false })}
                            className="btn btn-primary"
                        >
                            Try again
                        </button>
                        <Link href="/" className="btn btn-ghost">
                            Go home
                        </Link>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}

export default ErrorBoundary;
