"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { performanceData } from "@/lib/demo-data";

export function PerformanceChart() {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={performanceData} margin={{ top: 18, right: 4, left: -18, bottom: 0 }}>
          <defs><linearGradient id="googleFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2563eb" stopOpacity={0.24} /><stop offset="100%" stopColor="#2563eb" stopOpacity={0} /></linearGradient></defs>
          <CartesianGrid stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} />
          <YAxis axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} />
          <Tooltip contentStyle={{ borderRadius: 10, borderColor: "#dbeafe" }} />
          <Area type="monotone" dataKey="google" name="Google Ads" stroke="#2563eb" strokeWidth={2.5} fill="url(#googleFill)" />
          <Area type="monotone" dataKey="meta" name="Meta Ads" stroke="#d97706" strokeWidth={2.5} fill="transparent" />
        </AreaChart>
      </ResponsiveContainer>
      <details className="chart-table"><summary>View accessible data table</summary><table><thead><tr><th>Day</th><th>Google Ads</th><th>Meta Ads</th></tr></thead><tbody>{performanceData.map((row) => <tr key={row.date}><td>{row.date}</td><td>{row.google.toLocaleString()}</td><td>{row.meta.toLocaleString()}</td></tr>)}</tbody></table></details>
    </div>
  );
}
