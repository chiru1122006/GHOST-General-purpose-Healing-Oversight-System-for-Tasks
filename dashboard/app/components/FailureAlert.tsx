"use client";

// ─────────────────────────────────────────────
// FailureAlert — Failure event timeline
// ─────────────────────────────────────────────

interface Step {
  step_number: number;
  tool_name: string;
  failure_detected: boolean;
  failure_type: string | null;
  recovery_strategy: string | null;
  adherence_score: number | null;
}

interface FailureAlertProps {
  steps: Step[];
}

export default function FailureAlert({ steps }: FailureAlertProps) {
  const failures = steps.filter((s) => s.failure_detected);

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
        <span>⚠️</span>
        Failures
        {failures.length > 0 && (
          <span
            style={{
              fontSize: "10px",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "10px",
              background: "#ef444420",
              color: "var(--red)",
            }}
          >
            {failures.length}
          </span>
        )}
      </div>

      {failures.length === 0 ? (
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
          ✅ No failures detected
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "200px", overflowY: "auto" }}>
          {failures.map((f, i) => (
            <div
              key={i}
              style={{
                padding: "10px 12px",
                borderRadius: "8px",
                background: "#ef444408",
                border: "1px solid #ef444425",
                fontSize: "12px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                <span style={{ fontWeight: 600, color: "var(--red)" }}>
                  {f.failure_type || "unknown"}
                </span>
                <span style={{ color: "var(--muted)", fontSize: "11px" }}>
                  Step {f.step_number}
                </span>
              </div>
              <div style={{ color: "var(--muted)", fontSize: "11px" }}>
                Tool: <span style={{ color: "var(--foreground)" }}>{f.tool_name}</span>
                {f.adherence_score !== null && (
                  <> · Score: <span style={{ color: f.adherence_score < 0.4 ? "var(--red)" : "var(--amber)" }}>
                    {f.adherence_score.toFixed(2)}
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
