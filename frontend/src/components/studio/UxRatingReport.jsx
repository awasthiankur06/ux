function scoreColor(score) {
  if (score >= 8) return "bg-[#34C759]";
  if (score >= 5) return "bg-primary";
  return "bg-destructive";
}

export function UxRatingReport({ uxRating }) {
  if (!uxRating) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-xs p-6 text-center" data-testid="ux-rating-empty">
        UX Rating report appears here once a website URL is analyzed by the UX Critique Agent.
      </div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto h-full space-y-5" data-testid="ux-rating-report">
      <div className="border border-border p-4 text-center">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Overall Score</p>
        <p className="text-4xl font-chivo font-black text-primary mt-1" data-testid="ux-overall-score">
          {uxRating.overall_score}<span className="text-lg text-muted-foreground">/10</span>
        </p>
      </div>

      <div className="space-y-4">
        {(uxRating.categories || []).map((cat, i) => (
          <div key={i} data-testid={`ux-category-${i}`}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-white font-semibold">{cat.name}</span>
              <span className="text-muted-foreground">{cat.score}/10</span>
            </div>
            <div className="h-1.5 bg-muted w-full">
              <div className={`h-full ${scoreColor(cat.score)}`} style={{ width: `${cat.score * 10}%` }} />
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5 leading-relaxed">{cat.rationale}</p>
          </div>
        ))}
      </div>

      {uxRating.recommendations?.length > 0 && (
        <div className="border-t border-border pt-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-2">Recommendations</p>
          <ul className="text-[11px] text-muted-foreground space-y-1.5">
            {uxRating.recommendations.map((r, i) => (
              <li key={i} data-testid={`ux-recommendation-${i}`}>→ {r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
