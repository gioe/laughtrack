import { redirect } from "next/navigation";
export default function BlockedIntake() {
    redirect("/admin/reviews?view=intake&state=blocked");
}
