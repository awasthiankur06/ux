const SEVERITY_CLASS = {
  error: "border-destructive text-destructive",
  warning: "border-primary text-primary",
  info: "border-secondary text-secondary",
};

export function ComplianceReport({ report, designSystem, govAssets = [] }) {
  if (designSystem !== "dbim_gov") {
    return <div className="h-full flex items-center justify-center text-muted-foreground text-xs p-6 text-center" data-testid="compliance-report-standard">Gov Compliance - Design Pre-check is available for Gov-mode runs.</div>;
  }
  if (!report) {
    return <div className="h-full flex items-center justify-center text-muted-foreground text-xs p-6 text-center" data-testid="compliance-report-empty">The DBIM/GIGW pre-check report appears after Gov wireframe generation.</div>;
  }
  return (
    <div className="h-full overflow-y-auto p-4 space-y-3" data-testid="compliance-report">
      <div className="border border-border p-3">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{report.profile_label || "Gov Compliance - Design Pre-check"}</p>
        <p className={`text-lg font-chivo font-bold mt-1 ${report.passed ? "text-[#34C759]" : "text-destructive"}`}>{report.passed ? "No blocking findings" : "Manual action required"}</p>
        <p className="text-[10px] text-muted-foreground mt-1">{report.disclaimer || "Pre-check only - not an official GIGW certification."}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="border border-border p-2"><span className="text-muted-foreground">Errors</span><p className="text-destructive font-bold">{report.summary?.error || 0}</p></div>
        <div className="border border-border p-2"><span className="text-muted-foreground">Warnings</span><p className="text-primary font-bold">{report.summary?.warning || 0}</p></div>
      </div>
      {govAssets.length > 0 && <section className="border border-border p-3 text-[11px] space-y-2" data-testid="gov-asset-review"><p className="font-semibold uppercase text-[10px] tracking-[0.16em]">User-provided Gov assets</p>{govAssets.map((asset) => <div key={asset.id}><p className="font-medium">{asset.asset_type.replaceAll("_", " ")}: {asset.filename}</p><p className="text-muted-foreground">{asset.review_status?.replaceAll("_", " ")}. {asset.usage_note}</p></div>)}</section>}
      {(report.findings || []).map((finding, index) => <div key={index} className={`border-l-2 p-2 text-[11px] ${SEVERITY_CLASS[finding.severity] || "border-border"}`} data-testid={`compliance-finding-${index}`}><p className="font-semibold uppercase text-[10px]">{finding.severity} - {finding.rule_title || finding.rule}</p><p className="text-muted-foreground mt-1">{finding.screen_name ? `${finding.screen_name}: ` : ""}{finding.message}</p>{finding.source && <a className="mt-1 block text-[10px] underline text-muted-foreground" href={finding.source.url} target="_blank" rel="noreferrer">Source: {finding.source.document}</a>}</div>)}
      {(report.manual_review || []).length > 0 && <section className="border border-border p-3 text-[11px] space-y-2"><p className="font-semibold uppercase text-[10px] tracking-[0.16em]">Manual review still required</p>{report.manual_review.map((rule) => <div key={rule.rule}><p className="font-medium">{rule.title}</p><p className="text-muted-foreground">{rule.requirement}</p><a className="text-[10px] underline text-muted-foreground" href={rule.source.url} target="_blank" rel="noreferrer">Source: {rule.source.document}</a></div>)}</section>}
    </div>
  );
}
