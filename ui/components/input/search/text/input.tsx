interface TextInputComponentProps {
    icon: React.ReactNode;
    placeholder: string;
    value?: string;
    onChange?: (value: string) => void;
    className?: string;
}

const TextInputComponent = ({
    icon,
    placeholder,
    value,
    onChange,
    className = "",
}: TextInputComponentProps) => {
    return (
        <div className={`flex items-center flex-1 ${className}`}>
            {icon}
            <input
                type="text"
                placeholder={placeholder}
                value={value}
                onChange={(e) => onChange?.(e.target.value)}
                className="outline-none w-full bg-transparent focus:outline-none border-none focus:border-none font-dmSans text-[16px] text-cedar"
            />
        </div>
    );
};

export default TextInputComponent;
