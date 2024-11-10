"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import useLoginModal from "../../../../hooks/useLoginModal";
import Modal from "../..";
import toast from "react-hot-toast";
import LoginForm from "./form";
import { loginSchema } from "./form/schema";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

const LoginModal = () => {
    const router = useRouter();
    const loginModal = useLoginModal();
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof loginSchema>>({
        resolver: zodResolver(loginSchema),
        defaultValues: {
            username: "",
            password: "",
        },
    });

    const onSubmit = (data: z.infer<typeof loginSchema>) => {
        setIsLoading(true);

        signIn("credentials", {
            ...data,
            redirect: false,
        }).then((callback) => {
            setIsLoading(false);
            if (callback?.ok) {
                toast.success("Logged in");
                router.refresh();
                loginModal.onClose();
            }

            if (callback?.error) {
                toast.error(callback.error);
            }
        });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={loginModal.isOpen}
            title="Login"
            actionLabel="Continue"
            onClose={loginModal.onClose}
            onSubmit={form.handleSubmit(onSubmit)}
            body={<LoginForm isLoading={isLoading} form={form} />}
        />
    );
};

export default LoginModal;
