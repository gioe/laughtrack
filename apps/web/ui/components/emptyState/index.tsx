import { LucideIcon } from "lucide-react";
import { ReactNode } from "react";

interface EmptyStateProps {
    title: string;
    message: string;
    icons: LucideIcon[];
    action?: ReactNode;
}

const EmptyState = ({ title, message, icons, action }: EmptyStateProps) => {
    return (
        <div className="mx-auto flex w-full max-w-xl flex-col items-center justify-center px-4 py-16 text-center">
            <div className="w-full rounded-lg border border-white/10 bg-white/[0.035] px-6 py-8 shadow-sm shadow-black/20 sm:px-8">
                <div className="flex flex-col items-center gap-5">
                    <div className="flex items-center gap-3">
                        {icons.map((Icon, index) => (
                            <div
                                key={index}
                                className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-foreground/45"
                            >
                                <Icon className="h-5 w-5" strokeWidth={1.7} />
                            </div>
                        ))}
                    </div>
                    <div className="space-y-3">
                        <h2 className="font-dmSans text-2xl font-semibold text-foreground sm:text-3xl">
                            {title}
                        </h2>
                        <p className="font-dmSans text-base text-foreground/55 sm:text-lg">
                            {message}
                        </p>
                        {action && <div className="pt-2">{action}</div>}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default EmptyState;
