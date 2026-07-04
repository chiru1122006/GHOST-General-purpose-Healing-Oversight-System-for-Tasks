"use client";

// ─────────────────────────────────────────────
// StatsHeader — 4 stat cards at the top
// ─────────────────────────────────────────────

interface Stats {
  total_sessions: number;
  successful_sessions: number;
  success_rate: number;
  total_recoveries: number;
  total_failures: number;
  failure_breakdown: Record<string, number>;
  avg_adherence: number;
}

interface StatsHeaderProps {
  stats: Stats;
}

interface CardProps {
  label: string;
  value: string | number;
  sub?: string;
  color: string;
  icon: string;
}

function StatCard({ label, value, sub, color, icon }: CardProps) {
  return (
    <div
      style={{
        background: "var(--card)",
        borderRadius: "12px",
        padding: "20px",
        border: "1px solid var(--border)",
        position: "relative",
        overflow: "hidden",
        transition: "border-color 0.2s ease, transform 0.15s ease",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = color;
        (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
        (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
      }}
    >
      {/* Glow accent */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "2px",
          background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
          opacity: 0.6,
        }}
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            {label}
          </div>
          <div style={{ fontSize: "32px", fontWeight: 700, color }}>
            {value}
          </div>
          {sub && (
            <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "4px" }}>
              {sub}
            </div>
          )}
        </div>
        <div style={{ fontSize: "24px", opacity: 0.4 }}>{icon}</div>
      </div>
    </div>
  );
}

export default function StatsHeader({ stats }: StatsHeaderProps) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" }}>
      <StatCard
        label="Total Sessions"
        value={stats.total_sessions}
        sub={`${stats.successful_sessions} successful`}
        color="var(--blue)"
        icon="📊"
      />
      <StatCard
        label="Failures Detected"
        value={stats.total_failures}
        sub={Object.keys(stats.failure_breakdown).length + " failure types"}
        color="var(--red)"
        icon="⚠️"
      />
      <StatCard
        label="Recoveries Triggered"
        value={stats.total_recoveries}
        sub="autonomous repairs"
        color="var(--amber)"
        icon="🔧"
      />
      <StatCard
        label="Success Rate"
        value={`${stats.success_rate}%`}
        sub={`avg adherence: ${stats.avg_adherence.toFixed(2)}`}
        color="var(--green)"
        icon="✅"
      />
    </div>
  );
}
