import { ToastProvider } from "@/components/ToastProvider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { FileStagingProvider } from "@/features/files/FileStagingProvider";
import { BreakSheetProvider } from "@/features/breaks/BreakSheetProvider";
import { ReconciliationProvider } from "./providers/ReconciliationProvider";
import { Shell } from "./Shell";

export function App() {
  return (
    <ToastProvider>
      <TooltipProvider delayDuration={400}>
        <ReconciliationProvider>
          <BreakSheetProvider>
            <FileStagingProvider>
              <Shell />
            </FileStagingProvider>
          </BreakSheetProvider>
        </ReconciliationProvider>
      </TooltipProvider>
    </ToastProvider>
  );
}
