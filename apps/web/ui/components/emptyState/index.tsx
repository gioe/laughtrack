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
        <div className="flex flex-col items-center justify-center py-16 px-4 max-w-2xl mx-auto text-center">
            <div className="bg-gradient-to-br from-cream-50 to-cream-100 p-8 rounded-2xl shadow-lg mb-8">
                <div className="flex flex-col items-center gap-6">
                    <div className="flex items-center gap-4">
                        {icons.map((Icon, index) => (
                            <div
                                key={index}
                                className="p-4 bg-copper/10 rounded-full"
                            >
                                <Icon className="w-8 h-8 text-copper" />
                            </div>
                        ))}
                    </div>
                    <div className="space-y-4">
                        <h2 className="font-bold font-dmSans text-3xl sm:text-4xl text-cedar">
                            {title}
                        </h2>
                        <p className="text-gray-600 text-lg font-dmSans">
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
