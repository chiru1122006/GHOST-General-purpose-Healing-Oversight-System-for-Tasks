"use client";

// ─────────────────────────────────────────────
// SessionTable — Clickable session list
// ─────────────────────────────────────────────

interface Session {
  session_id: string;
  task_type: string;
  objective: string;
  status: string;
  total_steps: number;
  recovery_count: number;
  final_adherence: number | null;
  success: boolean;
  duration_seconds: number | null;
}

interface SessionTableProps {
  sessions: Session[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function getAdherenceColor(score: number | null): string {
  if (score === null) return "var(--muted)";
  if (score >= 0.7) return "var(--green)";
  if (score >= 0.4) return "var(--amber)";
  return "var(--red)";
}

function getStatusColor(status: string): string {
  switch (status) {
    case "completed": return "var(--green)";
    case "failed": return "var(--red)";
    case "running": return "var(--blue)";
    default: return "var(--muted)";
  }
}

function getStatusBg(status: string): string {
  switch (status) {
    case "completed": return "#22c55e15";
    case "failed": return "#ef444415";
    case "running": return "#3b82f615";
    default: return "#a1a1aa15";
  }
}

export default function SessionTable({ sessions, selectedId, onSelect }: SessionTableProps) {
  if (sessions.length === 0) {
    return (
      <div
        style={{
          background: "var(--card)",
          borderRadius: "12px",
          border: "1px solid var(--border)",
          padding: "48px 24px",
          textAlign: "center",
          color: "var(--muted)",
          fontSize: "14px",
        }}
      >
        <div style={{ fontSize: "32px", marginBottom: "12px" }}>👻</div>
        <p style={{ fontWeight: 500 }}>No sessions yet</p>
        <p style={{ fontSize: "13px", marginTop: "8px", opacity: 0.6 }}>
          Run <code style={{ color: "var(--amber)" }}>python examples/demo_simple.py</code> to generate data
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--card)",
        borderRadius: "12px",
        border: "1px solid var(--border)",
        overflow: "hidden",
        maxHeight: "calc(100vh - 260px)",
        overflowY: "auto",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "14px 16px",
          borderBottom: "1px solid var(--border)",
          fontSize: "12px",
          fontWeight: 600,
          color: "var(--muted)",
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          position: "sticky",
          top: 0,
          background: "var(--card)",
          zIndex: 1,
        }}
      >
        Sessions ({sessions.length})
      </div>

      {/* Rows */}
      {sessions.map((s) => {
        const isSelected = s.session_id === selectedId;
        return (
          <div
            key={s.session_id}
            onClick={() => onSelect(s.session_id)}
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--border)",
              cursor: "pointer",
              background: isSelected ? "#22c55e08" : "transparent",
              borderLeft: isSelected ? "3px solid var(--green)" : "3px solid transparent",
              transition: "background 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = "var(--card-hover)";
            }}
            onMouseLeave={(e) => {
              if (!isSelected) (e.currentTarget as HTMLElement).style.background = "transparent";
            }}
          >
            {/* Row top: ID + status */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <span style={{ fontFamily: "monospace", fontSize: "12px", fontWeight: 600 }}>
                {s.session_id.slice(0, 16)}
              </span>
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "10px",
                  background: getStatusBg(s.status),
                  color: getStatusColor(s.status),
                  textTransform: "uppercase",
                  letterSpacing: "0.3px",
                }}
              >
                {s.status}
              </span>
            </div>

            {/* Row bottom: task type + metrics */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "var(--muted)" }}>{s.task_type}</span>
              <div style={{ display: "flex", gap: "12px", alignItems: "center", fontSize: "12px" }}>
                <span style={{ color: "var(--muted)" }}>
                  {s.total_steps} steps
                </span>
                {s.recovery_count > 0 && (
                  <span style={{ color: "var(--amber)" }}>
                    🔧 {s.recovery_count}
                  </span>
                )}
                {s.final_adherence !== null && (
                  <span style={{ color: getAdherenceColor(s.final_adherence), fontWeight: 600 }}>
                    {s.final_adherence.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
