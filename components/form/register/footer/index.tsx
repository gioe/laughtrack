"use client";

interface RegistrationFormFooterProps {
    handleLoginClick: () => void;
}

export default function RegistrationFormFooter({
    handleLoginClick,
}: RegistrationFormFooterProps) {
    return (
        <div className="flex flex-col gap-4 mt-3">
            <hr />
            <div className="text-neutral-500 text-center mt-4 font-light">
                <div className="justify-center flex flex-row items-center gap-2">
                    <div>Already have an account?</div>
                    <div
                        onClick={handleLoginClick}
                        className="text-neutral-800 cursor-pointer hover:underline"
                    >
                        Log in
                    </div>
                </div>
            </div>
        </div>
    );
}
