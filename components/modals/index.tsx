"use client";

import React, { useCallback, useEffect, useState } from "react";
import { IoMdClose } from "react-icons/io";
import ButtonComponent from "../button";
import { Form } from "../ui/form";

interface ModalProps {
    isOpen?: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    form: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSubmit: (data: any) => void;
    onClose: () => void;
    title?: string;
    body?: React.ReactElement;
    footer?: React.ReactElement;
    actionLabel: string;
    disabled?: boolean;
    secondaryAction?: () => void;
    secondaryActionLabel?: string;
}

const Modal: React.FC<ModalProps> = ({
    form,
    onSubmit,
    isOpen,
    onClose,
    title,
    body,
    footer,
    actionLabel,
    disabled,
    secondaryAction,
    secondaryActionLabel,
}) => {
    const [showModal, setShowModal] = useState(isOpen);

    useEffect(() => {
        setShowModal(isOpen);
    }, [isOpen]);

    const handleClose = useCallback(() => {
        if (disabled) {
            return;
        }

        setShowModal(false);
        setTimeout(() => {
            onClose();
        }, 300);
    }, [disabled, onClose]);

    const handleSecondaryAction = useCallback(() => {
        if (disabled || !secondaryAction) {
            return;
        }
        secondaryAction();
    }, [disabled, secondaryAction]);

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
                        <Form {...form}>
                            <form
                                onSubmit={form.handleSubmit(onSubmit)}
                                className="translate h-full lg:h-auto md:h-auto border-0
                        rounded-lg shadow-lg relative flex flex-col w-full bg-shark
                        outline-none focus:outline-none"
                            >
                                <div className="flex items-center p-6 rounded-t justify-center relative border-b-[1px]">
                                    <div
                                        onClick={handleClose}
                                        className="cursor-pointer p-1 border-0 hover:opacity-70 transition absolute left-9"
                                    >
                                        <IoMdClose size={18} />
                                    </div>
                                    <div className="text-lg font-semibold">
                                        {title}
                                    </div>
                                </div>
                                <div className="relative p-6 flex-auto">
                                    {body}
                                </div>
                                <div className="flex flex-col gap-2 p-6">
                                    <div className="flex flex-row items-center gap-4 w-full">
                                        {secondaryAction &&
                                            secondaryActionLabel && (
                                                <ButtonComponent
                                                    outline
                                                    disabled={disabled}
                                                    label={secondaryActionLabel}
                                                    onClick={
                                                        handleSecondaryAction
                                                    }
                                                />
                                            )}
                                        <ButtonComponent
                                            type="submit"
                                            disabled={disabled}
                                            label={actionLabel}
                                        />
                                    </div>
                                    {footer}
                                </div>
                            </form>
                        </Form>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Modal;
