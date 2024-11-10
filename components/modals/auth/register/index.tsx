"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import useRegisterModal from "../../../../hooks/useRegisterModel";
import toast from "react-hot-toast";
import useLoginModal from "../../../../hooks/useLoginModal";
import axios from "axios";
import Modal from "../..";
import RegistrationForm from "./form";
import RegistrationFormFooter from "./form/footer";
import { z } from "zod";
import { registerSchema } from "./form/schema";
import { zodResolver } from "@hookform/resolvers/zod";

const RegisterModal = () => {
    const registerModal = useRegisterModal();
    const loginModal = useLoginModal();
    const router = useRouter();

    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof registerSchema>>({
        resolver: zodResolver(registerSchema),
        defaultValues: {
            email: "",
            password: "",
        },
    });

    const onSubmit = (data: z.infer<typeof registerSchema>) => {
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

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={registerModal.isOpen}
            title="Register"
            actionLabel="Continue"
            onClose={registerModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={<RegistrationForm isLoading={isLoading} form={form} />}
            footer={
                <RegistrationFormFooter handleLoginClick={handleLoginClick} />
            }
        />
    );
};

export default RegisterModal;
