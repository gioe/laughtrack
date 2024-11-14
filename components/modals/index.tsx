"use client";

import React, { useEffect, useState } from "react";

interface ModalProps {
    isOpen?: boolean;
    body?: React.ReactElement;
    footer?: React.ReactElement;
    onClose: () => void;
}

const Modal: React.FC<ModalProps> = ({ isOpen, body, footer }) => {
    const [showModal, setShowModal] = useState(isOpen);

    useEffect(() => {
        setShowModal(isOpen);
    }, [isOpen]);

    if (!isOpen) {
        return null;
    }

    return (
        <>
            <div
                className="justify-center items-center flex overflow-x-hidden overflow-y-auto
             fixed inset-0 z-50 outline-none focus:outline-none bg-neutral-800/70"
            >
                <div className="relative w-full md:w-4/6 lg:w-3/6 xl:w-2/5 my-6 mx-auto h-full lg:h-auto md:h-auto">
                    <div
                        className={`tranlate duration-300 h-full
                        ${showModal ? "translate-y-0" : "translate-y-full"}
                        ${showModal ? "opacity-100" : "opacity-0"}`}
                    >
                        <div
                            className="translate h-full lg:h-auto md:h-auto border-0
                        rounded-lg shadow-lg relative flex flex-col w-full bg-shark
                        outline-none focus:outline-none"
                        >
                            <div className="relative p-6 flex-auto">{body}</div>
                            {footer}
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Modal;
