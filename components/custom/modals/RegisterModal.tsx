"use client";

import { useState } from "react";
import { useForm, SubmitHandler, FieldValues } from "react-hook-form";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import useRegisterModal from "../../../hooks/useRegisterModel";
import Modal from "./Modal";
import Heading from "../Heading";
import toast from "react-hot-toast";
import useLoginModal from "../../../hooks/useLoginModal";
import axios from "axios";
import StylizedInput from "../input";

const RegisterModal = () => {
    const registerModal = useRegisterModal();
    const loginModal = useLoginModal();
    const router = useRouter();

    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<FieldValues>({
        defaultValues: {
            email: "",
            password: "",
        },
    });

    const onSubmit: SubmitHandler<FieldValues> = (data) => {
        setIsLoading(true);
        axios
            .post("/api/register", data)
            .then(() => {
                return signIn("credentials", {
                    ...data,
                    redirect: false,
                });
            })
            .then((callback) => {
                if (callback?.ok) {
                    toast.success("Logged in");
                    router.refresh();
                    loginModal.onClose();
                    registerModal.onClose();
                }

                if (callback?.error) {
                    toast.error(callback.error);
                }
            })
            .catch(() => toast.error("Something went wrong"))
            .finally(() => setIsLoading(false));
    };

    const handleLoginClick = () => {
        registerModal.onClose();
        loginModal.onOpen();
    };

    const bodyContent = (
        <div className="flex flex-col gap-4">
            <Heading
                title="Welcome to Laughtrack"
                subtitle="Create an account"
            />
            <StylizedInput
                id="email"
                label="Email"
                disabled={isLoading}
                register={register}
                errors={errors}
                required
            />
            <StylizedInput
                id="password"
                type="password"
                label="Password"
                disabled={isLoading}
                register={register}
                errors={errors}
                required
            />
        </div>
    );

    const footerContent = (
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

    return (
        <Modal
            form={}
            disabled={isLoading}
            isOpen={registerModal.isOpen}
            title="Register"
            actionLabel="Continue"
            onClose={registerModal.onClose}
            onSubmit={handleSubmit(onSubmit)}
            body={bodyContent}
            footer={footerContent}
        />
    );
};

export default RegisterModal;
