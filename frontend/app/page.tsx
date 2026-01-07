"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

type ComponentMap = Record<string, { score: number; weight: number }>;
type Driver = { id: string; name: string; impact: number; category: string };

type RHIResponse = {
  timestamp: string;
  headline_score: number;
  components: ComponentMap;
  driver_decomposition: Driver[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export default function RHIDashboard() {
  const [data, setData] = useState<RHIResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setError(null);
        const res = await fetch(`${API_BASE}/rhi/latest`, { cache: "no-store" });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const json = (await res.json()) as RHIResponse;
        if (alive) setData(json);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Unknown error");
      }
    }

    load();
    const t = setInterval(load, 60_000); // refresh every minute
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const radarData = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.components).map(([name, val]) => ({
      subject: name,
      score: val.score
    }));
  }, [data]);

  const statusLabel = (score: number) => {
    if (score < 40) return "High Stress";
    if (score < 60) return "Moderate Stress";
    return "Healthy-ish (for logistics)";
  };

  const scoreClass = (score: number) => {
    if (score < 40) return "text-red-600";
    if (score < 60) return "text-amber-600";
    return "text-emerald-600";
  };

  if (error) {
    return (
      <div className="p-10">
        <div className="max-w-xl rounded-2xl border border-red-200 bg-white p-6">
          <div className="text-lg font-semibold text-red-700">UI hit turbulence</div>
          <div className="mt-2 text-sm text-slate-600">
            Couldn't reach the backend at <span className="font-mono">{API_BASE}</span>.
          </div>
          <div className="mt-2 text-xs text-slate-500">Error: {error}</div>
        </div>
      </div>
    );
  }

  if (!data) return <div className="p-10">Loading Intelligence Engine…</div>;

  return (
    <div className="min-h-screen p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Radar Health Index</h1>
        <p className="text-slate-500">
          Real-time Supply Chain Health Monitor • Updated{" "}
          {new Date(data.timestamp).toLocaleString()}
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Headline Score */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>System Health</CardTitle>
          </CardHeader>
          <CardContent className="flex h-64 flex-col items-center justify-center">
            <div className={`text-6xl font-bold ${scoreClass(data.headline_score)}`}>
              {data.headline_score.toFixed(1)}
            </div>
            <div className="mt-2 text-slate-400">/ 100</div>
            <div className="mt-4 text-center text-sm text-slate-600">
              Status: <span className="font-semibold">{statusLabel(data.headline_score)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Component Balance</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tick={false}
                />
                <Radar
                  name="Health"
                  dataKey="score"
                  strokeWidth={2}
                  fillOpacity={0.25}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Driver Decomposition */}
        <Card className="md:col-span-3">
          <CardHeader>
            <CardTitle>Driver Decomposition (Today vs Yesterday)</CardTitle>
            <p className="text-xs text-slate-500">What actually moved the index?</p>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data.driver_decomposition}
                layout="vertical"
                margin={{ left: 24, right: 24 }}
              >
                <XAxis type="number" hide domain={["dataMin", "dataMax"]} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={180}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip />
                <Bar dataKey="impact" barSize={18}>
                  {data.driver_decomposition.map((d) => (
                    <Cell
                      key={d.id}
                      fill={d.impact >= 0 ? "#16a34a" : "#dc2626"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
