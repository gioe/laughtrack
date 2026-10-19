import { redirect } from "next/navigation";
export default function PodcastReviews() {
    redirect("/admin/reviews?view=relationships&kind=host_of");
}
