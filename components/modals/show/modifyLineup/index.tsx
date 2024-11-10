"use client";

import useModifyLineupModal from "../../../../hooks/useModifyLineupModal";
import Modal from "../..";
import axios from "axios";
import toast from "react-hot-toast";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Comedian } from "../../../../objects/classes/comedian/Comedian";
import { Show } from "../../../../objects/classes/show/Show";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { addComedianToShowSchema } from "./form/schema";
import { zodResolver } from "@hookform/resolvers/zod";
import AddComedianToShowForm from "./form";

interface ModifyLineupModalProps {
    showString: string;
}

const ModifyLineupModal: React.FC<ModifyLineupModalProps> = ({
    showString,
}) => {
    const show = JSON.parse(showString) as Show;
    const comedianChips = show.lineup.map((comedian: Comedian) => {
        return {
            id: comedian.id,
            name: comedian.name,
        };
    });
    const addComedianModal = useModifyLineupModal();

    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();

    const form = useForm<z.infer<typeof addComedianToShowSchema>>({
        resolver: zodResolver(addComedianToShowSchema),
        defaultValues: {
            showId: show.id,
            comedians: comedianChips,
        },
    });

    const onClose = () => {
        form.reset();
        addComedianModal.onClose();
    };

    const onSubmit = (data: z.infer<typeof addComedianToShowSchema>) => {
        setIsLoading(true);
        axios
            .put(`/api/show/${data.showId}/lineup`, {
                params: {
                    comedians: JSON.stringify(
                        data.comedians.map((comedian: Comedian) => comedian.id),
                    ),
                },
            })
            .then((response) => {
                if (response) {
                    setIsLoading(false);
                    toast.success("Successfully updated");
                    router.refresh();
                    addComedianModal.onClose();
                }
            })
            .catch((error) => {
                setIsLoading(false);
                toast.error(`Something went wrong: ${error.message}`);
            });
    };

    return (
        <Modal
            form={form}
            disabled={isLoading}
            isOpen={addComedianModal.isOpen}
            title="Modify Show Lineup"
            actionLabel="Submit"
            onClose={onClose}
            onSubmit={onSubmit}
            body={<AddComedianToShowForm show={show} form={form} />}
        />
    );
};

export default ModifyLineupModal;
