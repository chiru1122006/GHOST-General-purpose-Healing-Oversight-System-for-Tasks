"use client";

// ─────────────────────────────────────────────
// RecoveryLog — Recovery intervention timeline
// ─────────────────────────────────────────────

interface Step {
  step_number: number;
  tool_name: string;
  failure_detected: boolean;
  failure_type: string | null;
  recovery_triggered: boolean;
  recovery_strategy: string | null;
  adherence_score: number | null;
}

interface RecoveryLogProps {
  steps: Step[];
}

export default function RecoveryLog({ steps }: RecoveryLogProps) {
  const recoveries = steps.filter((s) => s.recovery_triggered);

  return (
    <div
      style={{
        background: "var(--card)",
        borderRadius: "12px",
        border: "1px solid var(--border)",
        padding: "16px",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
        <span>🔧</span>
        Recoveries
        {recoveries.length > 0 && (
          <span
            style={{
              fontSize: "10px",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "10px",
              background: "#f59e0b20",
              color: "var(--amber)",
            }}
          >
            {recoveries.length}
          </span>
        )}
      </div>

      {recoveries.length === 0 ? (
        <div
          style={{
            padding: "16px",
            borderRadius: "8px",
            background: "#22c55e10",
            border: "1px solid #22c55e30",
            fontSize: "13px",
            color: "var(--green)",
            textAlign: "center",
          }}
        >
          ✅ No recovery interventions needed
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "200px", overflowY: "auto" }}>
          {recoveries.map((r, i) => (
            <div
              key={i}
              style={{
                padding: "10px 12px",
                borderRadius: "8px",
                background: "#f59e0b08",
                border: "1px solid #f59e0b25",
                fontSize: "12px",
                position: "relative",
              }}
            >
              {/* Vertical timeline bar */}
              {i < recoveries.length - 1 && (
                <div
                  style={{
                    position: "absolute",
                    left: "6px",
                    top: "100%",
                    width: "2px",
                    height: "8px",
                    background: "#f59e0b30",
                  }}
                />
              )}

              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                <span style={{ fontWeight: 600, color: "var(--amber)" }}>
                  {r.recovery_strategy || "auto"}
                </span>
                <span style={{ color: "var(--muted)", fontSize: "11px" }}>
                  Step {r.step_number}
                </span>
              </div>
              <div style={{ color: "var(--muted)", fontSize: "11px" }}>
                Triggered by: <span style={{ color: "var(--red)" }}>
                  {r.failure_type || "anomaly"}
                </span>
                {r.adherence_score !== null && (
                  <> · Score after: <span style={{ color: "var(--green)" }}>
                    {r.adherence_score.toFixed(2)}
                  </span></>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
