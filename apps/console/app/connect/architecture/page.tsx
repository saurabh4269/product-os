import { redirect } from "next/navigation";

export default function ConnectArchitectureRedirect() {
  redirect("/labs/architecture?tab=overview");
}
