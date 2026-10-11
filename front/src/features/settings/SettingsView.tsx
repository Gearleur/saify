import { DataTable } from "@/components/DataTable";
import { ErrorNotice } from "@/components/ErrorNotice";
import { PageHeader } from "@/components/PageHeader";
import { Section } from "@/components/Section";
import { StatusLabel } from "@/components/StatusDot";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useReconciliation } from "@/hooks/useReconciliation";
import { CUSTODIAN_COLUMNS, FUND_COLUMNS, TYPE_COLUMNS } from "./settingsColumns";
import { MappingsTab } from "./MappingsTab";

/** Référentiel en lecture seule, tiré de parametrage.xlsx. */
export function SettingsView() {
  const { clientConfig: p, clientConfigError } = useReconciliation();
  return (
    <>
      <PageHeader
        title="Paramétrage"
        description="Lecture seule, tiré de parametrage.xlsx. Une modification se fait dans le fichier du client."
      />
      {clientConfigError && <ErrorNotice error={clientConfigError} />}
      {!p && !clientConfigError && <Skeleton className="h-48 w-full" />}
      {p && (
        <Tabs defaultValue="types">
          <TabsList>
            <TabsTrigger value="types">Types d'écarts</TabsTrigger>
            <TabsTrigger value="referentiel">Fonds et conservateurs</TabsTrigger>
            <TabsTrigger value="mappings">Transcodifications</TabsTrigger>
            <TabsTrigger value="exclusions">Exclusions</TabsTrigger>
          </TabsList>
          <TabsContent value="types">
            <DataTable
              label="Types d'écarts"
              rows={p.break_types}
              columns={TYPE_COLUMNS}
              getRowId={(t) => t.code}
            />
          </TabsContent>
          <TabsContent value="referentiel" className="grid gap-8 lg:grid-cols-2">
            <Section title="Fonds" count={p.fund.length}>
              <DataTable
                label="Fonds"
                rows={p.fund}
                columns={FUND_COLUMNS}
                getRowId={(f) => f.code}
              />
            </Section>
            <Section title="Conservateurs" count={p.custodians.length}>
              <DataTable
                label="Conservateurs"
                rows={p.custodians}
                columns={CUSTODIAN_COLUMNS}
                getRowId={(c) => c.code}
              />
            </Section>
          </TabsContent>
          <TabsContent value="mappings">
            <MappingsTab mappings={p.mappings} />
          </TabsContent>
          <TabsContent value="exclusions">
            <ul className="max-w-2xl">
              {p.exclusions.map((e) => (
                <li key={e} className="flex h-row items-center border-b border-border pl-1">
                  <StatusLabel tone="gray">{e}</StatusLabel>
                </li>
              ))}
            </ul>
          </TabsContent>
        </Tabs>
      )}
    </>
  );
}
