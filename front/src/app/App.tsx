import { ToastProvider } from "@/components/ToastProvider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { FileStagingProvider } from "@/features/files/FileStagingProvider";
import { SuspensSheetProvider } from "@/features/suspens/SuspensSheetProvider";
import { ReconciliationProvider } from "./providers/ReconciliationProvider";
import { Shell } from "./Shell";

export function App() {
  return (
    <ToastProvider>
      <TooltipProvider delayDuration={400}>
        <ReconciliationProvider>
          <SuspensSheetProvider>
            <FileStagingProvider>
              <Shell />
            </FileStagingProvider>
          </SuspensSheetProvider>
        </ReconciliationProvider>
      </TooltipProvider>
    </ToastProvider>
  );
}
