import { redirect } from "next/navigation";

/** Connect moved under Settings — keep old URL working. */
export default function ConnectRedirectPage() {
  redirect("/settings");
}
