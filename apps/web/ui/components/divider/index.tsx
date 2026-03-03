interface DropdownProps {
    text?: string;
}

export function Divider({ text }: DropdownProps) {
    return (
        <div className="relative">
            <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
                {text && (
                    <span className="px-2 bg-cream-50 text-gray-500">
                        {text}
                    </span>
                )}
            </div>
        </div>
    );
}
