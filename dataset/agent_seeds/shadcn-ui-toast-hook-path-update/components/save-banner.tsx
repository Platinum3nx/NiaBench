import { useToast } from "@/components/ui/use-toast";

export function SaveBanner() {
  const { toast } = useToast();
  return <button onClick={() => toast({ title: "Saved" })}>Save</button>;
}
