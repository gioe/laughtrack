interface DropdownProps {
    text?: string;
}

export function Divider({ text }: DropdownProps) {
    return (
        <div className="relative">
            <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-strong"></div>
            </div>
            <div className="relative flex justify-center text-sm">
                {text && (
                    <span className="px-2 bg-coconut-cream text-muted-foreground">
                        {text}
                    </span>
                )}
            </div>
        </div>
    );
}
