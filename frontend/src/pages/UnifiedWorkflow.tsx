import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import {
  Upload, FileText, CheckCircle2, Edit2, Users, Calendar, Shield,
  TrendingUp, Search, ArrowRight, AlertTriangle, Key, Eye, EyeOff,
  Info, X, ExternalLink, FlaskConical, Layers, MapPin, ChevronDown,
  ChevronRight, Activity, Pill, BarChart2, ClipboardList, Microscope,
  BookOpen, GitCompare, Star, AlertCircle, Globe, Database, FileCheck,
  Beaker, Heart, Stethoscope, Clock, Target, Building2,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import Navbar from "@/components/Navbar";
import ProtocolLoader from "@/components/ProtocalAnalyzerLoader";
import VendorIntelligenceLoader from "@/components/VendorIntelligenceLoader";
import DocumentLoader from "@/components/DocumentComparisonLoader";
import { API_BASE_URL, BLOB_URL } from "@/config/api";

// ─── Type Definitions ──────────────────────────────────────────────────────────

interface ChangeEntry {
  section: string;
  subsection: string | null;
  addons: string[];
  impacts: string[];
  removed: string[];
}
interface SubsectionEntry { subsection: string; content: string; }
interface SectionEntry { section: string; subsections: SubsectionEntry[] | null; content?: string; }
interface ParsedComparisonData { changes: ChangeEntry[]; additions: SectionEntry[]; removals: SectionEntry[]; }

interface CitationData {
  parameter: string;
  value: any;
  context?: string[];
  page_number?: (number | string)[];
  extracted_text?: string[];
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

const getPageNums = (obj: any): string[] => {
  const raw = obj?.page_number ?? obj?.page_numbers ?? [];
  return Array.isArray(raw) ? raw.map(String) : [];
};

const getCitationData = (src: any, label: string, value: any): CitationData => ({
  parameter: label,
  value,
  context: Array.isArray(src?.context) ? src.context : src?.context ? [src.context] : [],
  page_number: getPageNums(src),
  extracted_text: src?.extracted_text || [],
});

const hasCitationInfo = (src: any) =>
  getPageNums(src).length > 0 || (src?.extracted_text?.length ?? 0) > 0 || (src?.context?.length ?? 0) > 0;

const formatDuration = (val: any) => {
  if (!val || val === "N/A") return "N/A";
  const match = String(val).match(/[\d.]+/);
  if (match) {
    const num = parseFloat(match[0]);
    if (!isNaN(num)) return `${Math.ceil(num)} weeks`;
  }
  return val;
};

// ─── Citation Modal ────────────────────────────────────────────────────────────

const CitationModal = ({ isOpen, onClose, data, fileName }: {
  isOpen: boolean; onClose: () => void; data: CitationData | null; fileName: string;
}) => {
  useEffect(() => {
    if (!isOpen) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [isOpen, onClose]);

  if (!isOpen || !data) return null;
  const pageNumbers = data.page_number ?? [];
  const extractedText = data.extracted_text ?? [];
  const contextList = data.context ?? [];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div className="fixed inset-0 z-[99999] flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl flex flex-col"
            style={{ maxHeight: "85vh" }}
            initial={{ scale: 0.94, y: 16, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.94, y: 16, opacity: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-blue-700 to-blue-500 rounded-t-2xl flex-shrink-0">
              <h3 className="text-base font-semibold text-white">Citation Details — {data.parameter}</h3>
              <button onClick={onClose} className="text-white/80 hover:text-white hover:bg-white/20 rounded-lg p-1.5 transition-colors"><X className="h-4 w-4" /></button>
            </div>
            <div className="overflow-y-auto flex-1 p-6 space-y-5">
              {contextList.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Location in Document</h4>
                  <ul className="text-sm text-gray-700 bg-blue-50 rounded-lg px-3 py-2.5 border border-blue-100 space-y-1 list-disc list-inside">
                    {contextList.map((ctx, i) => <li key={i} className="break-words">{ctx}</li>)}
                  </ul>
                </section>
              )}
              {pageNumbers.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Pages / Sections</h4>
                  <div className="flex flex-wrap gap-2">
                    {pageNumbers.map((pg, idx) => {
                      const s = String(pg);
                      const isNum = /^\d+$/.test(s);
                      return (
                        <button key={idx}
                          onClick={() => isNum && window.open(`${BLOB_URL}${fileName}#page=${s}`, "_blank")}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${isNum ? "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 cursor-pointer" : "bg-gray-100 text-gray-600 border-gray-200 cursor-default"}`}
                        >
                          {isNum ? `Page ${s}` : s}
                          {isNum && <ExternalLink className="h-3 w-3" />}
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}
              {extractedText.length > 0 && (
                <section>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Source Text</h4>
                  <div className="space-y-2">
                    {extractedText.map((text, idx) => (
                      <div key={idx} className="text-xs bg-amber-50 text-gray-700 rounded-lg px-3 py-2.5 border border-amber-200 italic leading-relaxed">
                        <span className="not-italic text-amber-600 font-semibold mr-1">[{idx + 1}]</span>"{text}"
                      </div>
                    ))}
                  </div>
                </section>
              )}
              {pageNumbers.length === 0 && extractedText.length === 0 && contextList.length === 0 && (
                <p className="text-sm text-gray-400 italic text-center py-4">No citation details available.</p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// ─── Citation Button ───────────────────────────────────────────────────────────

const CitationBtn = ({ src, label, value, onCite }: {
  src: any; label: string; value: any; onCite: (d: CitationData) => void;
}) => {
  if (!hasCitationInfo(src)) return null;
  return (
    <button
      onClick={() => onCite(getCitationData(src, label, value))}
      className="ml-2 shrink-0 inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded text-[10px] font-medium border border-blue-200 transition-all"
    >
      Cite <ChevronDown className="w-3 h-3" />
    </button>
  );
};

// ─── Section Header ────────────────────────────────────────────────────────────

const SectionHeader = ({ icon: Icon, title, color = "text-blue-600" }: { icon: any; title: string; color?: string }) => (
  <div className={`flex items-center gap-2 mb-4 pb-2 border-b border-gray-100`}>
    <Icon className={`h-5 w-5 ${color}`} />
    <h3 className={`text-base font-semibold text-gray-800`}>{title}</h3>
  </div>
);

// ─── Field Row (label + value in a clean row) ─────────────────────────────────

const FieldRow = ({ label, value, src, onCite }: {
  label: string; value: any; src?: any; onCite?: (d: CitationData) => void;
}) => {
  const renderVal = (v: any): React.ReactNode => {
    if (v === null || v === undefined || v === "" || v === "N/A") return <span className="text-gray-400 italic text-sm">N/A</span>;
    if (typeof v === "boolean") return <span className="text-sm font-medium">{v ? "Yes" : "No"}</span>;
    if (typeof v === "number") return <span className="text-sm">{v}</span>;
    if (Array.isArray(v)) {
      const items = v.filter(i => i !== null && i !== undefined && i !== "");
      if (items.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
      if (items.length === 1) return <span className="text-sm text-gray-700">{typeof items[0] === "object" ? JSON.stringify(items[0]) : String(items[0])}</span>;
      return (
        <ul className="list-disc list-inside space-y-0.5 mt-0.5">
          {items.map((item, i) => (
            <li key={i} className="text-sm text-gray-700 break-words">
              {typeof item === "object" ? JSON.stringify(item) : String(item)}
            </li>
          ))}
        </ul>
      );
    }
    if (typeof v === "object") return <span className="text-sm text-gray-600 font-mono bg-gray-50 px-1 rounded">{JSON.stringify(v)}</span>;
    if (typeof v === "string") {
      if (v.includes("\n")) {
        return (
          <ul className="list-disc list-inside space-y-0.5 mt-0.5">
            {v.split("\n").filter(Boolean).map((line, i) => <li key={i} className="text-sm text-gray-700">{line}</li>)}
          </ul>
        );
      }
      return <span className="text-sm text-gray-700">{v}</span>;
    }
    return <span className="text-sm text-gray-700">{String(v)}</span>;
  };

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-50 last:border-0 group">
      <div className="w-44 flex-shrink-0 text-xs font-semibold text-gray-500 uppercase tracking-wide pt-0.5">{label}</div>
      <div className="flex-1 flex items-start justify-between gap-2 min-w-0">
        <div className="flex-1 min-w-0">{renderVal(value)}</div>
        {src && onCite && <CitationBtn src={src} label={label} value={value} onCite={onCite} />}
      </div>
    </div>
  );
};

// ─── KPI Card ──────────────────────────────────────────────────────────────────

const KPICard = ({ title, value, icon: Icon, color = "blue" }: { title: string; value: string; icon: any; color?: string }) => {
  const colors: Record<string, string> = {
    blue: "bg-blue-50 border-blue-100 text-blue-600",
    green: "bg-emerald-50 border-emerald-100 text-emerald-600",
    purple: "bg-purple-50 border-purple-100 text-purple-600",
    orange: "bg-orange-50 border-orange-100 text-orange-600",
    pink: "bg-pink-50 border-pink-100 text-pink-600",
    teal: "bg-teal-50 border-teal-100 text-teal-600",
  };
  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${colors[color]} transition-all hover:shadow-sm`}>
      <div className="w-9 h-9 rounded-lg bg-white/80 flex items-center justify-center shadow-sm flex-shrink-0">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70 leading-none mb-0.5">{title}</p>
        <p className="text-sm font-bold truncate">{value || "N/A"}</p>
      </div>
    </div>
  );
};

// ─── Endpoint Table ────────────────────────────────────────────────────────────

const EndpointTable = ({ endpoints, src, onCite }: { endpoints: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!endpoints || endpoints.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  const cols = ["Endpoint/Variable", "Population", "Timeframe", "Summary Measure", "Treatment of Interest", "Handling of intercurrent events"];
  const keyMap: Record<string, string> = {
    "Endpoint/Variable": "endpoint_variable", "Population": "population", "Timeframe": "timeframe",
    "Summary Measure": "summary_measure", "Treatment of Interest": "treatment_of_interest",
    "Handling of intercurrent events": "handling_of_intercurrent_events",
  };
  const hasData = (ep: any, col: string) => ep[keyMap[col]] && ep[keyMap[col]] !== "N/A";
  const activeCols = cols.filter(col => endpoints.some(ep => hasData(ep, col)));

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="px-3 pt-2 flex justify-end">
          <CitationBtn src={src} label="Endpoint" value={endpoints} onCite={onCite} />
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            {activeCols.map(col => <TableHead key={col} className="text-xs font-semibold text-gray-600 py-2 px-3 whitespace-nowrap">{col}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {endpoints.map((ep, i) => (
            <TableRow key={i} className="hover:bg-gray-50">
              {activeCols.map(col => (
                <TableCell key={col} className="text-sm text-gray-700 py-2 px-3 align-top">
                  {ep[keyMap[col]] || <span className="text-gray-300">—</span>}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

// ─── Lab Assessments Table ─────────────────────────────────────────────────────

const LabAssessmentsTable = ({ labs, src, onCite }: { labs: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!labs || labs.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="px-3 pt-2 flex justify-end">
          <CitationBtn src={src} label="Lab Assessments" value={labs} onCite={onCite} />
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            <TableHead className="text-xs font-semibold text-gray-600 py-2 px-3">Category</TableHead>
            <TableHead className="text-xs font-semibold text-gray-600 py-2 px-3">Tests</TableHead>
            <TableHead className="text-xs font-semibold text-gray-600 py-2 px-3">Frequency</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {labs.map((lab, i) => (
            <TableRow key={i} className="hover:bg-gray-50 align-top">
              <TableCell className="text-sm font-medium text-gray-800 py-2 px-3 whitespace-nowrap">{lab.lab_category || <span className="text-gray-300">—</span>}</TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3">
                {lab.tests?.length > 0 ? (
                  <ul className="list-disc list-inside space-y-0.5">{lab.tests.map((t: string, ti: number) => <li key={ti} className="text-xs">{t}</li>)}</ul>
                ) : <span className="text-gray-300">—</span>}
              </TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3">{lab.frequency || <span className="text-gray-300">—</span>}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

// ─── Assays Table ──────────────────────────────────────────────────────────────

const AssaysTable = ({ assays, src, onCite }: { assays: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!assays || assays.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="px-3 pt-2 flex justify-end"><CitationBtn src={src} label="Assays" value={assays} onCite={onCite} /></div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            {["Name", "Type", "Analyte", "Matrix", "Purpose", "Timing", "Population"].map(h => (
              <TableHead key={h} className="text-xs font-semibold text-gray-600 py-2 px-3 whitespace-nowrap">{h}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {assays.map((a, i) => (
            <TableRow key={i} className="hover:bg-gray-50 align-top">
              {[a.assay_name, a.assay_type, a.analyte, a.sample_matrix, a.purpose, a.timing, a.population].map((v, vi) => (
                <TableCell key={vi} className="text-sm text-gray-700 py-2 px-3">{v || <span className="text-gray-300">—</span>}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

// ─── Imaging Studies Table ─────────────────────────────────────────────────────

const ImagingTable = ({ imaging, src, onCite }: { imaging: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!imaging || imaging.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="px-3 pt-2 flex justify-end"><CitationBtn src={src} label="Imaging Studies" value={imaging} onCite={onCite} /></div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            {["Type", "Description", "Frequency"].map(h => <TableHead key={h} className="text-xs font-semibold text-gray-600 py-2 px-3">{h}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {imaging.map((img, i) => (
            <TableRow key={i} className="hover:bg-gray-50 align-top">
              <TableCell className="text-sm font-medium text-gray-800 py-2 px-3 whitespace-nowrap">{img.imaging_type || <span className="text-gray-300">—</span>}</TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3">{img.description || <span className="text-gray-300">—</span>}</TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3 whitespace-nowrap">{img.frequency || <span className="text-gray-300">—</span>}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

// ─── Prohibited Medications Block ──────────────────────────────────────────────

const ProhibitedMedsBlock = ({ meds, src, onCite }: { meds: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!meds || meds.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="space-y-3 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label="Prohibited Medications" value={meds} onCite={onCite} /></div>
      )}
      {meds.map((group, i) => (
        <div key={i} className="rounded-lg border border-red-100 bg-red-50 p-3">
          {group.category && <p className="text-xs font-bold text-red-700 uppercase tracking-wide mb-1.5">{group.category}</p>}
          {group.items?.length > 0 && (
            <ul className="list-disc list-inside space-y-0.5 mb-1.5">
              {group.items.map((item: string, ii: number) => <li key={ii} className="text-sm text-red-800">{item}</li>)}
            </ul>
          )}
          {group.details && <p className="text-xs text-red-600 italic border-t border-red-100 pt-1 mt-1">{group.details}</p>}
        </div>
      ))}
    </div>
  );
};

// ─── Background Therapy Block ──────────────────────────────────────────────────

const BackgroundTherapyBlock = ({ therapies, src, onCite }: { therapies: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!therapies || therapies.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="space-y-3 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label="Background Therapy" value={therapies} onCite={onCite} /></div>
      )}
      {therapies.map((group, i) => (
        <div key={i} className="rounded-lg border border-teal-100 bg-teal-50 p-3">
          {group.applicable_to && <p className="text-xs font-bold text-teal-700 uppercase tracking-wide mb-1.5">{group.applicable_to}</p>}
          {group.therapies?.map((t: any, ti: number) => (
            <div key={ti} className="flex items-start gap-2 py-1 border-b border-teal-100 last:border-0">
              <span className="text-sm font-medium text-teal-900 min-w-[140px]">{t.therapy_name}</span>
              {t.therapy_details && <span className="text-sm text-teal-700">{t.therapy_details}</span>}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

// ─── Efficacy Assessments Block ────────────────────────────────────────────────

const EfficacyAssessmentsBlock = ({ assessments, src, onCite }: { assessments: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!assessments || assessments.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="space-y-2 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label="Primary Efficacy Assessments" value={assessments} onCite={onCite} /></div>
      )}
      {assessments.map((a, i) => (
        <div key={i} className="rounded-lg border border-indigo-100 bg-indigo-50 p-3">
          <p className="text-sm font-semibold text-indigo-900">{a.assessment_name}</p>
          {a.assessment_short_description && <p className="text-xs text-indigo-700 mt-0.5">{a.assessment_short_description}</p>}
          {a.assessment_frequency && <p className="text-xs text-indigo-500 mt-1 italic">Frequency: {a.assessment_frequency}</p>}
        </div>
      ))}
    </div>
  );
};

// ─── PRO Block ─────────────────────────────────────────────────────────────────

const PROBlock = ({ pros, src, onCite }: { pros: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!pros || pros.length === 0) return <span className="text-gray-400 italic text-sm">None reported</span>;
  return (
    <div className="space-y-2 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label="Patient Reported Outcomes" value={pros} onCite={onCite} /></div>
      )}
      {pros.map((p, i) => (
        <div key={i} className="rounded-lg border border-purple-100 bg-purple-50 p-3">
          <p className="text-sm font-semibold text-purple-900">{p.pro_name}</p>
          {p.pro_description && <p className="text-xs text-purple-700 mt-0.5">{p.pro_description}</p>}
          {p.pro_frequency && <p className="text-xs text-purple-500 mt-1 italic">Frequency: {p.pro_frequency}</p>}
        </div>
      ))}
    </div>
  );
};

// ─── Exploratory / Safety Endpoints Block ──────────────────────────────────────

const EndpointListBlock = ({ endpoints, colorClass = "blue", src, onCite, label }: {
  endpoints: any[]; colorClass?: string; src?: any; onCite?: (d: CitationData) => void; label: string;
}) => {
  if (!endpoints || endpoints.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  const clr: Record<string, string> = {
    blue: "border-blue-100 bg-blue-50 text-blue-900 text-blue-700 list-blue",
    orange: "border-orange-100 bg-orange-50 text-orange-900 text-orange-700",
    green: "border-green-100 bg-green-50 text-green-900 text-green-700",
  };
  const c = clr[colorClass] || clr.blue;
  return (
    <div className="space-y-3 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label={label} value={endpoints} onCite={onCite} /></div>
      )}
      {endpoints.map((ep, i) => (
        <div key={i} className={`rounded-lg border p-3 ${c.split(" ").slice(0, 2).join(" ")}`}>
          <p className={`text-sm font-semibold ${c.split(" ")[2]} mb-1`}>{ep.endpoint || ep.assessment_name || ep.pro_name}</p>
          {ep.endpoint_description?.length > 0 && (
            <ul className="list-disc list-inside space-y-0.5">
              {ep.endpoint_description.map((d: string, di: number) => (
                <li key={di} className={`text-xs ${c.split(" ")[3]}`}>{d}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
};

// ─── Safety Monitoring Block ───────────────────────────────────────────────────

const SafetyMonitoringBlock = ({ monitoring, src, onCite }: { monitoring: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!monitoring || monitoring.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="space-y-2 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label="Safety Monitoring" value={monitoring} onCite={onCite} /></div>
      )}
      {monitoring.map((m, i) => (
        <div key={i} className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
          <div className="w-2 h-2 rounded-full bg-rose-400 mt-1.5 flex-shrink-0" />
          <div>
            {m.monitoring_component && <p className="text-sm font-semibold text-gray-800">{m.monitoring_component}</p>}
            {m.description && <p className="text-xs text-gray-600 mt-0.5">{m.description}</p>}
          </div>
        </div>
      ))}
    </div>
  );
};

// ─── Regulatory Frameworks Block ───────────────────────────────────────────────

const RegulatoryBlock = ({ frameworks, src, onCite }: { frameworks: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!frameworks || frameworks.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="space-y-2 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label="Regulatory Frameworks" value={frameworks} onCite={onCite} /></div>
      )}
      {frameworks.map((f, i) => (
        <div key={i} className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
          <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
          <div>
            {f.agency_name && <p className="text-sm font-semibold text-gray-800">{f.agency_name}</p>}
            {f.details && <p className="text-xs text-gray-600 mt-0.5">{f.details}</p>}
          </div>
        </div>
      ))}
    </div>
  );
};

// ─── Data Management Block ─────────────────────────────────────────────────────

const DataMgmtBlock = ({ items, src, onCite }: { items: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!items || items.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="space-y-2 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="flex justify-end"><CitationBtn src={src} label="Data Management" value={items} onCite={onCite} /></div>
      )}
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
          <div className="w-2 h-2 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
          <div>
            {item.component_name && <p className="text-sm font-semibold text-gray-800">{item.component_name}</p>}
            {item.description && <p className="text-xs text-gray-600 mt-0.5">{item.description}</p>}
          </div>
        </div>
      ))}
    </div>
  );
};

// ─── Statistical Plan Block ────────────────────────────────────────────────────

const StatPlanBlock = ({ plan, src, onCite }: { plan: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!plan || plan.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="px-3 pt-2 flex justify-end"><CitationBtn src={src} label="Statistical Plan" value={plan} onCite={onCite} /></div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            <TableHead className="text-xs font-semibold text-gray-600 py-2 px-3 w-48">Parameter</TableHead>
            <TableHead className="text-xs font-semibold text-gray-600 py-2 px-3">Value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {plan.map((p, i) => (
            <TableRow key={i} className="hover:bg-gray-50 align-top">
              <TableCell className="text-sm font-medium text-gray-800 py-2 px-3">{p.parameter_name || <span className="text-gray-300">—</span>}</TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3">{p.parameter_value || <span className="text-gray-300">—</span>}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

// ─── Protocol Version History Table ───────────────────────────────────────────

const VersionHistoryTable = ({ versions, src, onCite }: { versions: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!versions || versions.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="px-3 pt-2 flex justify-end"><CitationBtn src={src} label="Version History" value={versions} onCite={onCite} /></div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            {["Version", "Date", "Summary of Changes"].map(h => <TableHead key={h} className="text-xs font-semibold text-gray-600 py-2 px-3">{h}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {versions.map((v, i) => (
            <TableRow key={i} className="hover:bg-gray-50 align-top">
              <TableCell className="text-sm font-medium text-gray-800 py-2 px-3 whitespace-nowrap">{v.version_number || <span className="text-gray-300">—</span>}</TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3 whitespace-nowrap">{v.version_date || <span className="text-gray-300">—</span>}</TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3">{v.changes_summary || <span className="text-gray-300">—</span>}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

// ─── Treatment Arm Card ────────────────────────────────────────────────────────

const TreatmentArmCard = ({ arm, label, colorClass, src, onCite }: {
  arm: any; label: string; colorClass: string; src?: any; onCite?: (d: CitationData) => void;
}) => {
  if (!arm || Object.keys(arm).filter(k => arm[k]).length === 0) return null;
  const fields = [
    { key: "arm_type", label: "Arm Type" }, { key: "population_size", label: "Population Size" },
    { key: "drug_name", label: "Drug Name" }, { key: "drug_description", label: "Description" },
    { key: "dose", label: "Dose" }, { key: "route", label: "Route" },
    { key: "timing", label: "Timing" }, { key: "duration", label: "Duration" },
    { key: "packaging", label: "Packaging" },
  ];
  return (
    <div className={`rounded-xl border p-4 ${colorClass}`}>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-bold uppercase tracking-wide">{label}</p>
        {src && onCite && hasCitationInfo(src) && <CitationBtn src={src} label={label} value={arm} onCite={onCite} />}
      </div>
      <div className="space-y-2">
        {fields.filter(f => arm[f.key]).map(f => (
          <div key={f.key} className="flex items-start gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-wide opacity-60 w-28 flex-shrink-0 pt-0.5">{f.label}</span>
            <span className="text-sm">{arm[f.key]}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Operational Excellence Block ──────────────────────────────────────────────

const OperationalExcellenceBlock = ({ ops, src, onCite }: { ops: any[]; src?: any; onCite?: (d: CitationData) => void }) => {
  if (!ops || ops.length === 0) return <span className="text-gray-400 italic text-sm">N/A</span>;
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 mt-1">
      {src && onCite && hasCitationInfo(src) && (
        <div className="px-3 pt-2 flex justify-end"><CitationBtn src={src} label="Operational Excellence" value={ops} onCite={onCite} /></div>
      )}
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            <TableHead className="text-xs font-semibold text-gray-600 py-2 px-3 w-48">Component</TableHead>
            <TableHead className="text-xs font-semibold text-gray-600 py-2 px-3">Description</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {ops.map((op, i) => (
            <TableRow key={i} className="hover:bg-gray-50 align-top">
              <TableCell className="text-sm font-medium text-gray-800 py-2 px-3">{op.component_name || <span className="text-gray-300">—</span>}</TableCell>
              <TableCell className="text-sm text-gray-700 py-2 px-3">{op.description || <span className="text-gray-300">—</span>}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

// ─── Vendor Categories Detail Panel ───────────────────────────────────────────

const VendorCategoryPanel = ({ data, onCite }: { data: any; onCite: (d: CitationData) => void }) => {
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  const excludedKeys = ["page_number", "page_numbers", "context", "extracted_text", "value"];
  const categories = Object.entries(data).filter(([k]) => !excludedKeys.includes(k));
  if (categories.length === 0) return null;

  const sectionColors = [
    { key: "key_capabilities", label: "Key Capabilities", bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-800" },
    { key: "technical_requirements", label: "Technical Requirements", bg: "bg-purple-50", border: "border-purple-200", text: "text-purple-800" },
    { key: "risk_factors", label: "Risk Factors", bg: "bg-red-50", border: "border-red-200", text: "text-red-800" },
    { key: "critical_success_factors", label: "Critical Success Factors", bg: "bg-green-50", border: "border-green-200", text: "text-green-800" },
  ];

  return (
    <div className="space-y-6 mt-4">
      {categories.map(([catName, catData]: [string, any]) => (
        <Card key={catName} className="p-6 border border-gray-200 shadow-sm">
          <h3 className="text-lg font-bold mb-4 capitalize flex items-center gap-2">
            <Layers className="h-5 w-5 text-blue-600" />{catName}
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            {sectionColors.map(({ key, label, bg, border, text }) => {
              const section = catData?.[key];
              if (!section?.value?.length) return null;
              return (
                <div key={key} className={`p-3 rounded-lg ${bg} border ${border}`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className={`text-xs font-semibold ${text} uppercase tracking-wide`}>{label}</p>
                    {hasCitationInfo(section) && <CitationBtn src={section} label={label} value={section.value} onCite={onCite} />}
                  </div>
                  <ul className="list-disc list-inside space-y-1">
                    {section.value.map((item: string, i: number) => <li key={i} className={`text-sm ${text}`}>{item}</li>)}
                  </ul>
                </div>
              );
            })}
          </div>
        </Card>
      ))}
    </div>
  );
};

// ─── Main Protocol Results Renderer ───────────────────────────────────────────

const ProtocolResults = ({ protocolData, fileName, onCite }: {
  protocolData: any; fileName: string; onCite: (d: CitationData) => void;
}) => {
  console.log("[ProtocolResults] Rendering with protocolData:", protocolData);
  console.log("[ProtocolResults] fileName:", fileName);
  const r1 = protocolData?.final_result || {};
  const r2 = protocolData?.final_result2 || {};
  const r3 = protocolData?.final_result3 || {};
  const r4 = protocolData?.final_result4 || {};
  const r5 = protocolData?.final_result5 || {};
  console.log("[ProtocolResults] r1 (final_result):", r1);
  console.log("[ProtocolResults] r2 (final_result2):", r2);
  console.log("[ProtocolResults] r3 (final_result3):", r3);
  console.log("[ProtocolResults] r4 (final_result4):", r4);
  console.log("[ProtocolResults] r5 (final_result5):", r5);

  const vendorCats = r1.vendor_categories;
  console.log("[ProtocolResults] Vendor Categories:", vendorCats);
  const hasVendorCats = vendorCats && typeof vendorCats === "object" && !Array.isArray(vendorCats) &&
    Object.keys(vendorCats).filter(k => !["page_number", "page_numbers", "context", "extracted_text", "value"].includes(k)).length > 0;

  return (
    <Tabs defaultValue="overview" className="w-full">
      <TabsList className="w-full justify-start mb-6 flex-wrap gap-1 h-auto">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="design">Study Design</TabsTrigger>
        <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
        <TabsTrigger value="schedule">Visit Schedule</TabsTrigger>
        <TabsTrigger value="safety">Safety & Follow-up</TabsTrigger>
        <TabsTrigger value="treatment">Treatment Arms</TabsTrigger>
        <TabsTrigger value="monitoring">Monitoring & Ops</TabsTrigger>
        {hasVendorCats && <TabsTrigger value="vendors">Vendor Categories</TabsTrigger>}
      </TabsList>

      {/* ── TAB: Overview (from r1 + r5) ── */}
      <TabsContent value="overview" className="space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <KPICard title="Duration" value={r1.duration?.value ? formatDuration(r1.duration.value) : "N/A"} icon={Clock} color="blue" />
          <KPICard title="Patients" value={r1.participants?.value || r1.number_of_patients?.value || "N/A"} icon={Users} color="green" />
          <KPICard title="Sites" value={r1.number_of_sites?.value || r1.global_sites?.value || "N/A"} icon={Globe} color="purple" />
          <KPICard title="Phase" value={r2.phase?.value || "N/A"} icon={TrendingUp} color="orange" />
          <KPICard title="Study Type" value={Array.isArray(r2.study_type?.value) ? r2.study_type.value[0] : r2.study_type?.value || "N/A"} icon={FlaskConical} color="pink" />
          <KPICard title="Blinding" value={Array.isArray(r2.blinding?.value) ? r2.blinding.value[0] : r2.blinding?.value || "N/A"} icon={Shield} color="teal" />
          <KPICard title="Randomization" value={r2.randomization?.value || "N/A"} icon={Activity} color="blue" />
          <KPICard title="Pivotal Study" value={r1.pivotal_study?.pivotal_study != null ? (r1.pivotal_study.pivotal_study ? "Yes" : "No") : r1.pivotal_study?.value || "N/A"} icon={Star} color="orange" />
        </div>

        {/* Protocol Meta (r5) */}
        {(r5.Protocol_Number || r5.Trial_Code || r5.Program || r5.Indication) && (
          <Card className="p-6 border border-gray-200 shadow-sm">
            <SectionHeader icon={FileText} title="Protocol Identification" color="text-gray-600" />
            {r5.Protocol_Number && <FieldRow label="Protocol Number" value={r5.Protocol_Number?.value} src={r5.Protocol_Number} onCite={onCite} />}
            {r5.Trial_Code && <FieldRow label="Trial Code" value={r5.Trial_Code?.value} src={r5.Trial_Code} onCite={onCite} />}
            {r5.Program && <FieldRow label="Program" value={r5.Program?.value} src={r5.Program} onCite={onCite} />}
            {r5.Indication && <FieldRow label="Indication" value={r5.Indication?.value} src={r5.Indication} onCite={onCite} />}
          </Card>
        )}

        {/* Logistics */}
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Building2} title="Logistics & Operations" color="text-blue-600" />
          <FieldRow label="Duration" value={r1.duration?.value ? formatDuration(r1.duration.value) : "N/A"} src={r1.duration} onCite={onCite} />
          <FieldRow label="Region / Geography" value={r1.region?.value || r1.geographic_requirements?.value} src={r1.region || r1.geographic_requirements} onCite={onCite} />
          <FieldRow label="Number of Sites" value={r1.number_of_sites?.value || r1.global_sites?.value} src={r1.number_of_sites || r1.global_sites} onCite={onCite} />
          <FieldRow label="Number of Participants" value={r1.participants?.value || r1.number_of_patients?.value} src={r1.participants || r1.number_of_patients} onCite={onCite} />
          <FieldRow label="Key Requirements" value={r1.key_requirements?.value || r1.technical_requirements?.value} src={r1.key_requirements || r1.technical_requirements} onCite={onCite} />
          <FieldRow label="Risk Factors" value={r1.risk_factors?.value || r1.risk_assessments?.value} src={r1.risk_factors || r1.risk_assessments} onCite={onCite} />
          <FieldRow label="Pivotal Study" value={r1.pivotal_study?.pivotal_study != null ? (r1.pivotal_study.pivotal_study ? "Yes" : "No") : r1.pivotal_study?.value} src={r1.pivotal_study} onCite={onCite} />
          {r1.pivotal_study?.note && <FieldRow label="Pivotal Study Note" value={r1.pivotal_study.note} src={r1.pivotal_study} onCite={onCite} />}
        </Card>

        {/* Vendor categories list */}
        {r1.vendor_categories && (
          <Card className="p-6 border border-gray-200 shadow-sm">
            {/* Added Flex Container to hold the Header and the Citation Button */}
            <div className="flex items-center justify-between mb-4">
              <SectionHeader icon={Layers} title="Vendor Categories" color="text-indigo-600" />
              <CitationBtn
                src={r1.vendor_categories}
                label="Vendor Categories"
                value={Object.keys(r1.vendor_categories).filter(k => !["page_number", "page_numbers", "context", "extracted_text", "value"].includes(k))}
                onCite={onCite}
              />
            </div>

            {Array.isArray(r1.vendor_categories) ? (
              <div className="flex flex-wrap gap-2">
                {r1.vendor_categories.map((cat: string, i: number) => (
                  <Badge key={i} variant="secondary" className="text-sm">{cat}</Badge>
                ))}
              </div>
            ) : typeof r1.vendor_categories === "object" ? (
              <div className="flex flex-wrap gap-2">
                {Object.keys(r1.vendor_categories)
                  .filter(k => !["page_number", "page_numbers", "context", "extracted_text", "value"].includes(k))
                  .map((cat, i) => <Badge key={i} variant="secondary" className="text-sm">{cat}</Badge>)}
              </div>
            ) : <FieldRow label="Vendor Categories" value={r1.vendor_categories} />}
          </Card>
        )}
      </TabsContent>

      {/* ── TAB: Study Design ── */}
      <TabsContent value="design" className="space-y-6">
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={FlaskConical} title="Study Design & Methodology" color="text-blue-600" />
          <FieldRow label="Study Type" value={r2.study_type?.value} src={r2.study_type} onCite={onCite} />
          <FieldRow label="Phase" value={r2.phase?.value} src={r2.phase} onCite={onCite} />
          <FieldRow label="Randomization" value={r2.randomization?.value} src={r2.randomization} onCite={onCite} />
          <FieldRow label="Blinding" value={r2.blinding?.value} src={r2.blinding} onCite={onCite} />
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Target} title="Objectives" color="text-green-600" />
          <FieldRow label="Primary Objective" value={r2.primary_objective?.value} src={r2.primary_objective} onCite={onCite} />
          <FieldRow label="Secondary Objective" value={r2.secondary_objective?.value} src={r2.secondary_objective} onCite={onCite} />
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Users} title="Population & Sample" color="text-purple-600" />
          <FieldRow label="Target Population" value={r2.target_population?.value} src={r2.target_population} onCite={onCite} />
          <FieldRow label="Sample Size" value={r2.sample_size?.value} src={r2.sample_size} onCite={onCite} />
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Activity} title="Dose Modification" color="text-orange-600" />
          <FieldRow label="Dose Modification Rules" value={r2.dose_modification?.value} src={r2.dose_modification} onCite={onCite} />
        </Card>
      </TabsContent>

      {/* ── TAB: Endpoints ── */}
      <TabsContent value="endpoints" className="space-y-6">
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Target} title="Primary Endpoints" color="text-blue-600" />
          {r2.primary_endpoint?.primary_endpoints?.length > 0 ? (
            <EndpointTable endpoints={r2.primary_endpoint.primary_endpoints} src={r2.primary_endpoint} onCite={onCite} />
          ) : (
            <FieldRow label="Primary Endpoint" value={r2.primary_endpoint?.primary_endpoints?.length > 0 ? r2.primary_endpoint.primary_endpoints : "N/A"} src={r2.primary_endpoint} onCite={onCite} />
          )}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={BarChart2} title="Secondary Endpoints" color="text-green-600" />
          {r2.secondary_endpoint?.secondary_endpoints?.length > 0 ? (
            <EndpointTable endpoints={r2.secondary_endpoint.secondary_endpoints} src={r2.secondary_endpoint} onCite={onCite} />
          ) : (
            <FieldRow
              label="Secondary Endpoint"
              value={
                r2.secondary_endpoint?.secondary_endpoints?.length > 0
                  ? r2.secondary_endpoint.secondary_endpoints
                  : "N/A"
              }
              src={r2.secondary_endpoint}
              onCite={onCite}
            />
          )}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={BookOpen} title="Exploratory Endpoints" color="text-orange-600" />
          {r4.exploratory_endpoints?.exploratory_endpoints?.length > 0 ? (
            <EndpointListBlock endpoints={r4.exploratory_endpoints.exploratory_endpoints} colorClass="orange" src={r4.exploratory_endpoints} onCite={onCite} label="Exploratory Endpoints" />
          ) : (
            <FieldRow label="Exploratory Endpoints" value={r4.exploratory_endpoints?.value} src={r4.exploratory_endpoints} onCite={onCite} />
          )}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={AlertCircle} title="Safety Endpoints" color="text-red-600" />
          {r4.safety_endpoints?.safety_endpoints?.length > 0 ? (
            <EndpointListBlock endpoints={r4.safety_endpoints.safety_endpoints} colorClass="orange" src={r4.safety_endpoints} onCite={onCite} label="Safety Endpoints" />
          ) : (
            <FieldRow label="Safety Endpoints" value={r4.safety_endpoints?.value} src={r4.safety_endpoints} onCite={onCite} />
          )}
        </Card>
      </TabsContent>

      {/* ── TAB: Visit Schedule ── */}
      <TabsContent value="schedule" className="space-y-6">
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Calendar} title="Pre-Screening Period" color="text-gray-600" />
          <FieldRow label="Period" value={r2.pre_screening?.period_days} src={r2.pre_screening} onCite={onCite} />
          <div className="py-2.5 border-b border-gray-50">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Assessments</div>
            {r2.pre_screening?.assessments?.length > 0 ? (
              <ul className="list-disc list-inside space-y-0.5">
                {r2.pre_screening.assessments.map((a: string, i: number) => <li key={i} className="text-sm text-gray-700">{a}</li>)}
              </ul>
            ) : <span className="text-gray-400 italic text-sm">N/A</span>}
          </div>
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Calendar} title="Screening Period" color="text-blue-600" />
          <FieldRow label="Period" value={r2.screening_period?.period_days} src={r2.screening_period} onCite={onCite} />
          <div className="py-2.5 border-b border-gray-50">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Assessments</div>
            {r2.screening_period?.assessments?.length > 0 ? (
              <ul className="list-disc list-inside space-y-0.5">
                {r2.screening_period.assessments.map((a: string, i: number) => <li key={i} className="text-sm text-gray-700">{a}</li>)}
              </ul>
            ) : <span className="text-gray-400 italic text-sm">N/A</span>}
          </div>
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Calendar} title="Treatment Period" color="text-green-600" />
          <FieldRow label="Timepoints" value={r2.treatment_period?.timepoints} src={r2.treatment_period} onCite={onCite} />
          <div className="py-2.5 border-b border-gray-50">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Assessments</div>
            {r2.treatment_period?.assessments?.length > 0 ? (
              <ul className="list-disc list-inside space-y-0.5">
                {r2.treatment_period.assessments.map((a: string, i: number) => <li key={i} className="text-sm text-gray-700">{a}</li>)}
              </ul>
            ) : <span className="text-gray-400 italic text-sm">N/A</span>}
          </div>
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Calendar} title="End of Treatment" color="text-orange-600" />
          <FieldRow label="Timepoint" value={r3.end_of_treatment?.timepoint} src={r3.end_of_treatment} onCite={onCite} />
          <div className="py-2.5">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Assessments</div>
            {r3.end_of_treatment?.assessments?.length > 0 ? (
              <ul className="list-disc list-inside space-y-0.5">
                {r3.end_of_treatment.assessments.map((a: string, i: number) => <li key={i} className="text-sm text-gray-700">{a}</li>)}
              </ul>
            ) : <span className="text-gray-400 italic text-sm">N/A</span>}
          </div>
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Calendar} title="Safety Follow-Up" color="text-red-600" />
          <FieldRow label="Timepoints" value={r3.safety_follow_up?.timepoints} src={r3.safety_follow_up} onCite={onCite} />
          <div className="py-2.5">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Assessments</div>
            {r3.safety_follow_up?.assessments?.length > 0 ? (
              <ul className="list-disc list-inside space-y-0.5">
                {r3.safety_follow_up.assessments.map((a: string, i: number) => <li key={i} className="text-sm text-gray-700">{a}</li>)}
              </ul>
            ) : <span className="text-gray-400 italic text-sm">N/A</span>}
          </div>
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Clock} title="Visit Windows" color="text-gray-600" />
          <FieldRow label="Visit Windows" value={r3.visit_windows?.value} src={r3.visit_windows} onCite={onCite} />
        </Card>
      </TabsContent>

      {/* ── TAB: Safety & Follow-up ── */}
      <TabsContent value="safety" className="space-y-6">
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={BarChart2} title="Stratification" color="text-indigo-600" />
          <FieldRow label="Stratification Factors" value={r3.stratification_factors?.value} src={r3.stratification_factors} onCite={onCite} />
          <FieldRow label="Rescue Therapy" value={r3.rescue_therapy?.value} src={r3.rescue_therapy} onCite={onCite} />
          <FieldRow label="Interim Analyses" value={r3.interim_analyses?.value} src={r3.interim_analyses} onCite={onCite} />
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Microscope} title="Assays" color="text-blue-600" />
          {r3.assays?.assays?.length > 0 ? (
            <AssaysTable assays={r3.assays.assays} src={r3.assays} onCite={onCite} />
          ) : <FieldRow label="Assays" value={r3.assays?.value} src={r3.assays} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Activity} title="Primary Efficacy Assessments" color="text-green-600" />
          {r3.primary_efficacy_assessments?.primary_efficacy_assessments?.length > 0 ? (
            <EfficacyAssessmentsBlock assessments={r3.primary_efficacy_assessments.primary_efficacy_assessments} src={r3.primary_efficacy_assessments} onCite={onCite} />
          ) : <FieldRow label="Efficacy Assessments" value={r3.primary_efficacy_assessments?.value} src={r3.primary_efficacy_assessments} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Heart} title="Patient Reported Outcomes" color="text-pink-600" />
          {r3.patient_reported_outcomes?.patient_reported_outcomes?.length > 0 ? (
            <PROBlock pros={r3.patient_reported_outcomes.patient_reported_outcomes} src={r3.patient_reported_outcomes} onCite={onCite} />
          ) : <FieldRow label="PROs" value={r3.patient_reported_outcomes?.value} src={r3.patient_reported_outcomes} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Pill} title="Background Therapy" color="text-teal-600" />
          {r3.background_therapy?.background_therapy?.length > 0 ? (
            <BackgroundTherapyBlock therapies={r3.background_therapy.background_therapy} src={r3.background_therapy} onCite={onCite} />
          ) : <FieldRow label="Background Therapy" value={r3.background_therapy?.value} src={r3.background_therapy} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Beaker} title="Laboratory Assessments" color="text-blue-600" />
          {r2.lab_assessments?.laboratory_assessments?.length > 0 ? (
            <LabAssessmentsTable labs={r2.lab_assessments.laboratory_assessments} src={r2.lab_assessments} onCite={onCite} />
          ) : <FieldRow label="Lab Assessments" value={r2.lab_assessments?.value} src={r2.lab_assessments} onCite={onCite} />}
        </Card>
      </TabsContent>

      {/* ── TAB: Treatment Arms ── */}
      <TabsContent value="treatment" className="space-y-6">
        <div className="grid md:grid-cols-2 gap-6">
          <TreatmentArmCard arm={r4.active_treatment_arm} label="Active Treatment Arm" colorClass="border-blue-200 bg-blue-50 text-blue-900" src={r4.active_treatment_arm} onCite={onCite} />
          <TreatmentArmCard arm={r4.control_arm} label="Control Arm" colorClass="border-gray-200 bg-gray-50 text-gray-900" src={r4.control_arm} onCite={onCite} />
        </div>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={AlertTriangle} title="Prohibited Medications" color="text-red-600" />
          {r4.prohibited_medications?.prohibited_medications?.length > 0 ? (
            <ProhibitedMedsBlock meds={r4.prohibited_medications.prohibited_medications} src={r4.prohibited_medications} onCite={onCite} />
          ) : <FieldRow label="Prohibited Medications" value={r4.prohibited_medications?.value} src={r4.prohibited_medications} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Stethoscope} title="Imaging Studies" color="text-indigo-600" />
          {r4.imaging_studies?.imaging_studies?.length > 0 ? (
            <ImagingTable imaging={r4.imaging_studies.imaging_studies} src={r4.imaging_studies} onCite={onCite} />
          ) : <FieldRow label="Imaging Studies" value={r4.imaging_studies?.value} src={r4.imaging_studies} onCite={onCite} />}
        </Card>
      </TabsContent>

      {/* ── TAB: Monitoring & Ops ── */}
      <TabsContent value="monitoring" className="space-y-6">
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Shield} title="Safety Monitoring" color="text-red-600" />
          {r4.safety_monitoring?.safety_monitoring?.length > 0 ? (
            <SafetyMonitoringBlock monitoring={r4.safety_monitoring.safety_monitoring} src={r4.safety_monitoring} onCite={onCite} />
          ) : <FieldRow label="Safety Monitoring" value={r4.safety_monitoring?.value} src={r4.safety_monitoring} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Globe} title="Regulatory Frameworks" color="text-blue-600" />
          {r4.regulatory_frameworks?.regulatory_frameworks?.length > 0 ? (
            <RegulatoryBlock frameworks={r4.regulatory_frameworks.regulatory_frameworks} src={r4.regulatory_frameworks} onCite={onCite} />
          ) : <FieldRow label="Regulatory Frameworks" value={r4.regulatory_frameworks?.value} src={r4.regulatory_frameworks} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Database} title="Data Management & Quality" color="text-cyan-600" />
          {r4.data_management_quality?.data_management_quality?.length > 0 ? (
            <DataMgmtBlock items={r4.data_management_quality.data_management_quality} src={r4.data_management_quality} onCite={onCite} />
          ) : <FieldRow label="Data Management" value={r4.data_management_quality?.value} src={r4.data_management_quality} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={BarChart2} title="Statistical Analytical Plan" color="text-purple-600" />
          {r4.statistical_analytical_plan?.statistical_analytical_plan?.length > 0 ? (
            <StatPlanBlock plan={r4.statistical_analytical_plan.statistical_analytical_plan} src={r4.statistical_analytical_plan} onCite={onCite} />
          ) : <FieldRow label="Statistical Plan" value={r4.statistical_analytical_plan?.value} src={r4.statistical_analytical_plan} onCite={onCite} />}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={FileCheck} title="Protocol Version History" color="text-gray-600" />
          {r4.protocol_version_history?.protocol_version_history?.length > 0 ? (
            <VersionHistoryTable versions={r4.protocol_version_history.protocol_version_history} src={r4.protocol_version_history} onCite={onCite} />
          ) : (
            <>
              <FieldRow label="Version History" value={r4.protocol_version_history?.value} src={r4.protocol_version_history} onCite={onCite} />
              {r4.protocol_version_history?.note && <FieldRow label="Note" value={r4.protocol_version_history.note} />}
            </>
          )}
        </Card>
        <Card className="p-6 border border-gray-200 shadow-sm">
          <SectionHeader icon={Building2} title="Operational Excellence" color="text-teal-600" />
          {r3.operational_excellence?.operational_excellence?.length > 0 ? (
            <OperationalExcellenceBlock ops={r3.operational_excellence.operational_excellence} src={r3.operational_excellence} onCite={onCite} />
          ) : <FieldRow label="Operational Excellence" value={r3.operational_excellence?.value} src={r3.operational_excellence} onCite={onCite} />}
        </Card>
      </TabsContent>

      {/* ── TAB: Vendor Categories ── */}
      {hasVendorCats && (
        <TabsContent value="vendors" className="space-y-4">
          {/* Added Flex container for Badges and the Citation Button */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex flex-wrap gap-2">
              {Object.keys(vendorCats)
                .filter(k => !["page_number", "page_numbers", "context", "extracted_text", "value"].includes(k))
                .map((cat, i) => (
                  <div key={i} className="px-4 py-2 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center gap-2">
                    <Layers className="h-4 w-4 text-indigo-600" />
                    <span className="font-medium text-sm text-indigo-900">{cat}</span>
                  </div>
                ))}
            </div>
            {/* Root level Citation Button */}
            <CitationBtn
              src={vendorCats}
              label="Vendor Categories"
              value={Object.keys(vendorCats).filter(k => !["page_number", "page_numbers", "context", "extracted_text", "value"].includes(k))}
              onCite={onCite}
            />
          </div>
          <VendorCategoryPanel data={vendorCats} onCite={onCite} />
        </TabsContent>
      )}
    </Tabs>
  );
};

// ─── Workflow Steps ────────────────────────────────────────────────────────────

const StepIndicator = ({ step, isCompleted, isActive, isAnimating, label }: {
  step: number; isCompleted: boolean; isActive: boolean; isAnimating: boolean; label: string;
}) => (
  <div className="flex flex-col items-center">
    <motion.div
      className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all ${isCompleted ? "bg-emerald-500 border-emerald-500 text-white" : isActive ? "bg-blue-600 border-blue-600 text-white" : "bg-background border-border text-muted-foreground"}`}
      animate={isAnimating ? { scale: [1, 1.1, 1] } : {}}
      transition={{ repeat: isAnimating ? Infinity : 0, duration: 1.5 }}
    >
      {isCompleted ? <CheckCircle2 className="h-6 w-6" /> : <span className="text-lg font-bold">{step}</span>}
    </motion.div>
    <span className="text-xs mt-2 text-center font-medium">{label}</span>
  </div>
);

const ArrowConnector = ({ isCompleted, isAnimating, icon: Icon }: { isCompleted: boolean; isAnimating: boolean; icon: any }) => (
  <div className="flex flex-col items-center my-2 relative">
    <motion.div className="w-0.5 h-24 bg-border relative overflow-hidden">
      <motion.div className="w-full bg-emerald-500 absolute top-0 left-0"
        initial={{ height: "0%" }}
        animate={{ height: isCompleted ? "100%" : isAnimating ? "50%" : "0%" }}
        transition={{ duration: 0.8, ease: "easeInOut" }}
      />
    </motion.div>
    {isAnimating && (
      <motion.div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-primary/20 p-2 rounded-full"
        animate={{ y: ["-100%", "100%"], opacity: [0, 1, 1, 0] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        <Icon className="h-4 w-4 text-primary" />
      </motion.div>
    )}
  </div>
);

// ─── Comparison helpers ────────────────────────────────────────────────────────

const isChangeLeaf = (obj: unknown): obj is Record<string, unknown> => {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) return false;
  const o = obj as Record<string, unknown>;
  return "addons" in o || "removed" in o || "impact" in o;
};
const isNewSectionLeaf = (obj: unknown): obj is Record<string, unknown> => {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) return false;
  const o = obj as Record<string, unknown>;
  return "Impact" in o || "impact" in o;
};
const toStringArray = (val: unknown): string[] => {
  if (!val) return [];
  if (Array.isArray(val)) return val.map(v => typeof v === "string" ? v : JSON.stringify(v));
  if (typeof val === "string") return [val];
  return [JSON.stringify(val)];
};
const makeChangeEntry = (section: string, subsection: string | null, data: Record<string, unknown>): ChangeEntry => ({
  section, subsection, addons: toStringArray(data.addons), impacts: toStringArray(data.impact), removed: toStringArray(data.removed),
});
const parseComparisonData = (comparisonResult: any): ParsedComparisonData => {
  console.log("[parseComparisonData] Input comparisonResult:", comparisonResult);
  if (!comparisonResult) { console.log("[parseComparisonData] No comparison result, returning empty"); return { changes: [], additions: [], removals: [] }; }
  const result: ParsedComparisonData = { changes: [], additions: [], removals: [] };
  const differences = (comparisonResult.differences ?? {}) as Record<string, unknown>;
  const newSections = (comparisonResult.new_sections ?? {}) as Record<string, unknown>;
  console.log("[parseComparisonData] differences:", differences);
  console.log("[parseComparisonData] newSections:", newSections);

  Object.entries(differences).forEach(([section, sectionData]) => {
    if (!sectionData || typeof sectionData !== "object") return;
    if (isChangeLeaf(sectionData)) { result.changes.push(makeChangeEntry(section, null, sectionData as Record<string, unknown>)); }
    else {
      Object.entries(sectionData as Record<string, unknown>).forEach(([subsection, subData]) => {
        if (!subData || typeof subData !== "object") return;
        if (isChangeLeaf(subData)) { result.changes.push(makeChangeEntry(section, subsection, subData as Record<string, unknown>)); }
        else {
          Object.entries(subData as Record<string, unknown>).forEach(([subSub, deepData]) => {
            if (deepData && typeof deepData === "object" && isChangeLeaf(deepData))
              result.changes.push(makeChangeEntry(section, `${subsection} › ${subSub}`, deepData as Record<string, unknown>));
          });
        }
      });
    }
  });
  result.changes = result.changes.filter(item => item.addons.some(Boolean) || item.impacts.some(Boolean) || item.removed.some(Boolean));

  const processSection = (sectionData: Record<string, unknown>, target: SectionEntry[]) => {
    Object.entries(sectionData).forEach(([section, data]) => {
      if (!data || typeof data !== "object") return;
      if (isNewSectionLeaf(data)) {
        const d = data as Record<string, unknown>;
        target.push({ section, subsections: null, content: String(d.Impact ?? d.impact ?? "") });
      } else {
        const subsections: SubsectionEntry[] = [];
        Object.entries(data as Record<string, unknown>).forEach(([subsection, d]) => {
          if (d && typeof d === "object" && isNewSectionLeaf(d)) {
            const dd = d as Record<string, unknown>;
            subsections.push({ subsection, content: String(dd.Impact ?? dd.impact ?? "") });
          }
        });
        if (subsections.length > 0) target.push({ section, subsections });
      }
    });
  };
  processSection((newSections.added ?? {}) as Record<string, unknown>, result.additions);
  processSection((newSections.removed ?? {}) as Record<string, unknown>, result.removals);
  console.log("[parseComparisonData] Output parsed result:", result);
  console.log("[parseComparisonData] Changes count:", result.changes.length, "Additions count:", result.additions.length, "Removals count:", result.removals.length);
  return result;
};

const renderStringList = (items: string[]) => (
  <ul className="list-disc list-inside text-sm text-muted-foreground mt-1 space-y-1">
    {items.filter(Boolean).map((item, i) => <li key={i} className="break-words">{typeof item === "string" ? item : JSON.stringify(item)}</li>)}
  </ul>
);

const renderSectionCard = (section: SectionEntry, index: number, borderColor: string, bgColor: string, labelColor: string) => (
  <motion.div key={index} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05 }}>
    <Card className={`p-4 border-l-4 ${borderColor} ${bgColor}`}>
      <h4 className="font-semibold mb-3 capitalize">{section.section}</h4>
      {section.subsections ? (
        <div className="space-y-3">
          {section.subsections.map((sub, si) => (
            <Card key={si} className="p-3 bg-white border border-border/20">
              <p className={`text-sm font-medium ${labelColor} mb-2 capitalize`}>{sub.subsection}</p>
              <p className="text-sm text-muted-foreground">{sub.content}</p>
            </Card>
          ))}
        </div>
      ) : (
        <div className={`p-2 rounded border border-border/10 ${bgColor}`}>
          <p className="text-sm text-muted-foreground">{section.content}</p>
        </div>
      )}
    </Card>
  </motion.div>
);

// ─── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [uploadedProtocol, setUploadedProtocol] = useState<File | null>(null);
  const [isAnalyzingProtocol, setIsAnalyzingProtocol] = useState(false);
  const [protocolData, setProtocolData] = useState<any>(null);
  const [citationModal, setCitationModal] = useState<CitationData | null>(null);
  const [citationFileName, setCitationFileName] = useState("");

  const [vendorName, setVendorName] = useState("Labcorp");
  const [vendorCategory, setVendorCategory] = useState("");
  const [isSearchingVendor, setIsSearchingVendor] = useState(false);
  const [vendorData, setVendorData] = useState<any>(null);
  const [isEditingVendor, setIsEditingVendor] = useState(false);
  const [apiResponseReceived, setApiResponseReceived] = useState(false);

  const [tavilyKeyInput, setTavilyKeyInput] = useState("");
  const [tavilyKey, setTavilyKey] = useState("");
  const [showTavilyKey, setShowTavilyKey] = useState(false);
  const [showTavilyInfo, setShowTavilyInfo] = useState(false);

  const [secondDocument, setSecondDocument] = useState<File | null>(null);
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [canReuploadFirst, setCanReuploadFirst] = useState(false);
  const [activeStep, setActiveStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [animatingArrow, setAnimatingArrow] = useState<number | null>(null);

  const openCitation = (data: CitationData, fileName?: string) => {
    console.log("[openCitation] Citation data:", data);
    console.log("[openCitation] fileName:", fileName);
    setCitationModal(data);
    setCitationFileName(fileName || uploadedProtocol?.name || "document.pdf");
  };

  const protocolDropzone = useDropzone({
    accept: { "application/pdf": [".pdf"] }, maxFiles: 1,
    onDrop: (files) => { if (files.length > 0) { console.log("[Step 1] Protocol file dropped:", files[0].name, "Size:", files[0].size, "bytes"); setUploadedProtocol(files[0]); } },
  });
  const secondDocDropzone = useDropzone({
    accept: { "application/pdf": [".pdf"] }, maxFiles: 1,
    onDrop: (files) => { if (files.length > 0) { console.log("[Step 3] Second document dropped:", files[0].name, "Size:", files[0].size, "bytes"); setSecondDocument(files[0]); } },
  });
  const reuploadDropzone = useDropzone({
    accept: { "application/pdf": [".pdf"] }, maxFiles: 1,
    onDrop: (files) => { if (files.length > 0) { console.log("[Step 3] Re-upload protocol file dropped:", files[0].name, "Size:", files[0].size, "bytes"); setUploadedProtocol(files[0]); setCanReuploadFirst(false); } },
  });

  const handleAnalyzeProtocol = async () => {
    console.log("[Step 1] ===== PROTOCOL ANALYSIS STARTED =====");
    console.log("[Step 1] Input file:", uploadedProtocol?.name, "Size:", uploadedProtocol?.size, "bytes");
    setActiveStep(1); setCompletedSteps([]); setAnimatingArrow(null);
    setIsAnalyzingProtocol(true);
    try {
      const formData = new FormData();
      formData.append("file", uploadedProtocol!);
      console.log("[Step 1] API Call: POST", `${API_BASE_URL}/process-pdf/`);
      console.log("[Step 1] Sending FormData with file:", uploadedProtocol!.name);
      const response = await fetch(`${API_BASE_URL}/process-pdf/`, { method: "POST", body: formData });
      console.log("[Step 1] API Response status:", response.status, response.statusText);
      const result = await response.json();
      console.log("[Step 1] API Response JSON (full):", result);
      console.log("[Step 1] API Response result.result:", result.result);
      setProtocolData(result.result);
      setIsAnalyzingProtocol(false);
      setCompletedSteps([1]);
      setActiveStep(2);
      const vendorCategoriesValue = result.result?.final_result?.vendor_categories;
      console.log("[Step 1] Extracted vendor_categories:", vendorCategoriesValue);
      let extractedCategory = "Central Lab";
      if (vendorCategoriesValue && typeof vendorCategoriesValue === "object" && !Array.isArray(vendorCategoriesValue)) {
        const keys = Object.keys(vendorCategoriesValue).filter(k => !["page_number", "page_numbers", "context", "extracted_text", "value"].includes(k));
        if (keys.length > 0) extractedCategory = keys[0];
      } else if (Array.isArray(vendorCategoriesValue) && vendorCategoriesValue.length > 0) extractedCategory = vendorCategoriesValue[0];
      else if (typeof vendorCategoriesValue === "string") extractedCategory = vendorCategoriesValue;
      console.log("[Step 1] Extracted vendor category for Step 2:", extractedCategory);
      setVendorCategory(extractedCategory);
      console.log("[Step 1] ===== PROTOCOL ANALYSIS COMPLETE =====");
    } catch (error) {
      console.error("[Step 1] ===== PROTOCOL ANALYSIS FAILED =====");
      console.error("[Step 1] Error:", error);
      setIsAnalyzingProtocol(false);
    }
  };

  const handleSearchVendor = async () => {
    console.log("[Step 2] ===== VENDOR SEARCH STARTED =====");
    if (!tavilyKey) { console.log("[Step 2] No Tavily key set, aborting"); return; }
    console.log("[Step 2] Input - vendorName:", vendorName);
    console.log("[Step 2] Input - vendorCategory:", vendorCategory);
    console.log("[Step 2] Input - tavilyKey:", tavilyKey ? "[SET]" : "[NOT SET]");
    setActiveStep(2); setCompletedSteps([1]); setAnimatingArrow(null);
    setIsSearchingVendor(true); setAnimatingArrow(2);
    setVendorData(null); setApiResponseReceived(false);
    try {
      const requestBody = { vendor_name: vendorName, vendor_category: vendorCategory, tavily_api_key: tavilyKey };
      console.log("[Step 2] API Call: POST", `${API_BASE_URL}/vendor-search/`);
      console.log("[Step 2] Request body:", { ...requestBody, tavily_api_key: "[REDACTED]" });
      const response = await fetch(`${API_BASE_URL}/vendor-search/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      console.log("[Step 2] API Response status:", response.status, response.statusText);
      const data = await response.json();
      console.log("[Step 2] API Response JSON (full):", data);
      if (data.success) {
        console.log("[Step 2] Vendor data output:", data.output);
        console.log("[Step 2] Capabilities:", data.output?.capabilities);
        console.log("[Step 2] Positive news:", data.output?.positive_news);
        console.log("[Step 2] Negative news:", data.output?.negative_news);
        setVendorData(data.output); setApiResponseReceived(true);
      }
      else { console.error("[Step 2] API Error:", data.error); setApiResponseReceived(true); }
      console.log("[Step 2] ===== VENDOR SEARCH COMPLETE =====");
    } catch (error) {
      console.error("[Step 2] ===== VENDOR SEARCH FAILED =====");
      console.error("[Step 2] Network Error:", error);
      setApiResponseReceived(true);
    }
  };

  const handleVendorLoaderComplete = () => {
    console.log("[Step 2] Vendor loader animation complete, transitioning to Step 3");
    setIsSearchingVendor(false); setCompletedSteps([1, 2]); setActiveStep(3); setAnimatingArrow(null);
  };
  const handleCompareDocuments = () => {
    console.log("[Step 3] ===== DOCUMENT COMPARISON STARTED =====");
    console.log("[Step 3] Input - Original document:", uploadedProtocol?.name, "Size:", uploadedProtocol?.size, "bytes");
    console.log("[Step 3] Input - Updated document:", secondDocument?.name, "Size:", secondDocument?.size, "bytes");
    if (uploadedProtocol && secondDocument) { setActiveStep(3); setCompletedSteps([1, 2]); setIsComparing(true); setAnimatingArrow(3); }
    else { console.log("[Step 3] Missing documents, cannot compare"); }
  };
  const handleComparisonComplete = (data: any) => {
    console.log("[Step 3] ===== DOCUMENT COMPARISON COMPLETE =====");
    console.log("[Step 3] Comparison output data:", data);
    console.log("[Step 3] Differences:", data?.differences);
    console.log("[Step 3] New sections:", data?.new_sections);
    setComparisonData(data); setIsComparing(false); setCompletedSteps([1, 2, 3]); setAnimatingArrow(null);
  };

  return (
    <div className="min-h-screen pb-20">
      <Navbar />
      <div className="pt-32 px-6">
        <div className="flex gap-6">
          {/* Sidebar */}
          <div className="w-[10%] min-w-[100px]">
            <Card className="glass-card p-6 pb-6 sticky top-24">
              <div className="flex flex-col items-center">
                <StepIndicator step={1} isCompleted={completedSteps.includes(1)} isActive={activeStep === 1} isAnimating={isAnalyzingProtocol} label="Protocol" />
                <ArrowConnector isCompleted={completedSteps.includes(1)} isAnimating={animatingArrow === 1 || (isAnalyzingProtocol && !completedSteps.includes(1))} icon={FileText} />
                <StepIndicator step={2} isCompleted={completedSteps.includes(2)} isActive={activeStep === 2} isAnimating={isSearchingVendor} label="Vendor" />
                <ArrowConnector isCompleted={completedSteps.includes(2)} isAnimating={animatingArrow === 2} icon={FileText} />
                <StepIndicator step={3} isCompleted={completedSteps.includes(3)} isActive={activeStep === 3} isAnimating={isComparing} label="Compare" />
              </div>
            </Card>
          </div>

          {/* Main */}
          <div className="flex-1">
            <div className="container mx-auto max-w-6xl">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
                <h1 className="text-4xl font-bold mb-4 gradient-text">Clinical Trial Agent</h1>
                <p className="text-lg text-muted-foreground">End-to-end protocol analysis, vendor research, and document comparison</p>
              </motion.div>

              {/* ── STEP 1 ── */}
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 mb-12">
                <Card className="glass-card p-12">
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold mb-2">Step 1: Upload Protocol Document</h2>
                    <p className="text-muted-foreground">Start by uploading your clinical trial protocol for analysis</p>
                  </div>
                  <div {...protocolDropzone.getRootProps()} className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${protocolDropzone.isDragActive ? "border-primary bg-primary/5 scale-105" : "border-border hover:border-primary hover:bg-primary/5"}`}>
                    <input {...protocolDropzone.getInputProps()} />
                    <Upload className="h-16 w-16 mx-auto mb-4 text-primary" />
                    <h3 className="text-xl font-semibold mb-2">{protocolDropzone.isDragActive ? "Drop your file here" : "Upload Protocol Document"}</h3>
                    <p className="text-muted-foreground">Drag & drop your PDF file or click to browse</p>
                  </div>
                  {uploadedProtocol && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-6 space-y-4">
                      <div className="flex items-center justify-between p-4 bg-primary/5 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <FileText className="h-5 w-5 text-primary" />
                          <span className="font-medium">{uploadedProtocol.name}</span>
                        </div>
                        <button onClick={() => setUploadedProtocol(null)} className="text-sm text-muted-foreground hover:text-foreground transition-colors">Change File</button>
                      </div>
                      <Button onClick={handleAnalyzeProtocol} disabled={isAnalyzingProtocol} variant="gradient" className="w-full">
                        {isAnalyzingProtocol ? "Analyzing..." : "Run Protocol Analysis"}
                      </Button>
                    </motion.div>
                  )}
                </Card>

                {isAnalyzingProtocol && <Card className="glass-card p-8"><ProtocolLoader /></Card>}

                {/* ── RESULTS ── */}
                {protocolData && !isAnalyzingProtocol && (
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                    <Card className="glass-card p-6">
                      <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center space-x-3">
                          <FileText className="h-6 w-6 text-primary" />
                          <span className="font-medium">{uploadedProtocol?.name}</span>
                        </div>
                        <Badge className="bg-emerald-500 text-white">
                          <CheckCircle2 className="h-4 w-4 mr-1" /> Analysis Complete
                        </Badge>
                      </div>
                      <ProtocolResults
                        protocolData={protocolData}
                        fileName={uploadedProtocol?.name || "document.pdf"}
                        onCite={(data) => openCitation(data, uploadedProtocol?.name)}
                      />
                    </Card>
                  </motion.div>
                )}
              </motion.div>

              {/* ── STEP 2: Vendor ── */}
              {protocolData && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 mb-12">
                  <Card className="glass-card p-8">
                    <div className="flex items-center justify-between mb-6">
                      <div>
                        <h2 className="text-2xl font-bold mb-2">Step 2: Vendor Market Analysis</h2>
                        <p className="text-muted-foreground">Research vendor capabilities and market position</p>
                      </div>
                      <Badge className="bg-emerald-500 text-white"><CheckCircle2 className="h-4 w-4 mr-1" />Ready</Badge>
                    </div>

                    {/* Tavily Info Modal */}
                    <AnimatePresence>
                      {showTavilyInfo && (
                        <motion.div className="fixed inset-0 z-50 flex items-center justify-center px-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowTavilyInfo(false)} />
                          <motion.div className="relative z-10 w-full max-w-md rounded-2xl p-6 space-y-5"
                            style={{ background: "var(--card)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 24px 60px rgba(0,0,0,0.3)" }}
                            initial={{ scale: 0.92, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.92, y: 12 }}
                            transition={{ type: "spring", stiffness: 300, damping: 25 }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2"><Key className="h-5 w-5 text-primary" /><h3 className="text-lg font-semibold">How to get a Tavily API Key</h3></div>
                            </div>
                            <ol className="space-y-3 text-sm text-muted-foreground">
                              {[
                                <span>Visit <a href="https://app.tavily.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-1">app.tavily.com <ExternalLink className="h-3 w-3" /></a></span>,
                                "Sign up for a free account (no credit card needed for the free tier).",
                                <span>Go to <span className="font-medium text-foreground">API Keys</span> in your dashboard.</span>,
                                <span>Click <span className="font-medium text-foreground">Create API Key</span> and copy the key.</span>,
                                "Paste it in the field below to enable vendor intelligence searches.",
                              ].map((step, i) => (
                                <li key={i} className="flex gap-3">
                                  <span className="flex-shrink-0 w-5 h-5 rounded-full text-xs flex items-center justify-center font-semibold" style={{ background: "var(--primary)", color: "white" }}>{i + 1}</span>
                                  <span className="pt-0.5">{step}</span>
                                </li>
                              ))}
                            </ol>
                            <Button onClick={() => setShowTavilyInfo(false)} className="w-full" variant="gradient">Got it</Button>
                          </motion.div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* API Key */}
                    <div className="mb-6 p-4 rounded-xl border border-border bg-muted/30">
                      <div className="flex items-center gap-2 mb-3">
                        <Key className="h-4 w-4 text-primary flex-shrink-0" />
                        <span className="text-sm font-medium">Tavily API Key</span>
                        {tavilyKey && <Badge variant="secondary" className="ml-auto text-xs bg-green-500/15 text-green-400 border border-green-500/20">✓ Key set</Badge>}
                      </div>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <Input type={showTavilyKey ? "text" : "password"} placeholder="tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" value={tavilyKeyInput} onChange={(e) => setTavilyKeyInput(e.target.value)} className="glass-card pr-10 font-mono text-sm" />
                          <button type="button" onClick={() => setShowTavilyKey(v => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors">
                            {showTavilyKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                        <Button onClick={() => { if (tavilyKeyInput.trim()) setTavilyKey(tavilyKeyInput.trim()); }} disabled={!tavilyKeyInput.trim()} variant="gradient" className="px-5 shrink-0">{tavilyKey ? "Update" : "Set Key"}</Button>
                      </div>
                      {!tavilyKey && (
                        <p className="text-xs text-muted-foreground mt-2">
                          A Tavily key is required.{" "}
                          <a
                            href="https://app.tavily.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                          >
                            Click here to get one
                          </a>
                        </p>
                      )}
                    </div>

                    <div className="grid md:grid-cols-2 gap-4 mb-6">
                      <div>
                        <label className="block text-sm font-medium mb-2">Vendor Name</label>
                        <div className="flex items-center space-x-2">
                          <Input value={vendorName} onChange={(e) => setVendorName(e.target.value)} disabled={!isEditingVendor} className="glass-card" />
                          <Button variant="outline" size="sm" onClick={() => setIsEditingVendor(!isEditingVendor)}><Edit2 className="h-4 w-4" /></Button>
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Vendor Category {vendorCategory && <Badge variant="secondary" className="ml-2">Auto-filled</Badge>}</label>
                        <Input value={vendorCategory} onChange={(e) => setVendorCategory(e.target.value)} className="glass-card" placeholder="Category from protocol analysis" />
                      </div>
                    </div>
                    <Button onClick={handleSearchVendor} disabled={!vendorName || !tavilyKey || isSearchingVendor} variant="gradient" className="w-full">
                      <Search className="h-4 w-4 mr-2" />{isSearchingVendor ? "Searching..." : "Run Vendor Analysis"}
                    </Button>
                  </Card>

                  {isSearchingVendor && (
                    <Card className="glass-card overflow-hidden">
                      <VendorIntelligenceLoader message="Analyzing global sources..." vendorName={vendorName} vendorCategory={vendorCategory} apiResponseReceived={apiResponseReceived} onComplete={handleVendorLoaderComplete} />
                    </Card>
                  )}

                  {vendorData && !isSearchingVendor && (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                      <Accordion type="multiple" defaultValue={["capabilities", "positive", "negative"]} className="space-y-4">
                        {vendorData.capabilities?.vendor_capabilities && (
                          <AccordionItem value="capabilities" className="glass-card border-0">
                            <AccordionTrigger className="px-6 py-4 hover:no-underline">
                              <div className="flex items-center space-x-3"><CheckCircle2 className="h-6 w-6 text-primary" /><span className="text-xl font-semibold">Capabilities</span><Badge variant="secondary">{vendorData.capabilities.vendor_capabilities.length}</Badge></div>
                            </AccordionTrigger>
                            <AccordionContent className="px-6 pb-6">
                              <div className="space-y-4">
                                {vendorData.capabilities.vendor_capabilities.map((item: any, index: number) => (
                                  <motion.div key={index} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.1 }}>
                                    <Card className="p-4 hover:shadow-card-hover transition-all">
                                      <div className="flex items-start justify-between mb-2"><h4 className="font-semibold">{item.title}</h4><Badge variant="outline" className="ml-2">{item.type}</Badge></div>
                                      <p className="text-sm text-muted-foreground mb-2">{item.summary}</p>
                                      {item.facts?.length > 0 && <ul className="text-xs text-gray-600 mb-2 list-disc list-inside">{item.facts.map((f: string, fi: number) => <li key={fi}>{f}</li>)}</ul>}
                                      <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline">Source: {item.source_url}</a>
                                    </Card>
                                  </motion.div>
                                ))}
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        )}
                        {vendorData.positive_news?.vendor_positive_news && (
                          <AccordionItem value="positive" className="glass-card border-0">
                            <AccordionTrigger className="px-6 py-4 hover:no-underline">
                              <div className="flex items-center space-x-3"><TrendingUp className="h-6 w-6 text-emerald-500" /><span className="text-xl font-semibold">Positive News</span><Badge variant="secondary">{vendorData.positive_news.vendor_positive_news.length}</Badge></div>
                            </AccordionTrigger>
                            <AccordionContent className="px-6 pb-6">
                              <div className="space-y-4">
                                {vendorData.positive_news.vendor_positive_news.map((item: any, index: number) => (
                                  <motion.div key={index} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.1 }}>
                                    <Card className="p-4 border-l-4 border-emerald-500 hover:shadow-card-hover transition-all">
                                      <div className="flex items-start justify-between mb-2">
                                        <div className="flex-1"><h4 className="font-semibold">{item.title}</h4><Badge variant="outline" className="mt-1">{item.type}</Badge></div>
                                        <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">{item.date && new Date(item.date).toLocaleDateString()}</span>
                                      </div>
                                      <p className="text-sm text-muted-foreground mb-2">{item.summary}</p>
                                      {item.facts?.length > 0 && <ul className="text-xs text-gray-600 mb-2 list-disc list-inside">{item.facts.map((f: string, fi: number) => <li key={fi}>{f}</li>)}</ul>}
                                      <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline">Source: {item.source_url}</a>
                                    </Card>
                                  </motion.div>
                                ))}
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        )}
                        {vendorData.negative_news?.vendor_negative_news && (
                          <AccordionItem value="negative" className="glass-card border-0">
                            <AccordionTrigger className="px-6 py-4 hover:no-underline">
                              <div className="flex items-center space-x-3"><AlertTriangle className="h-6 w-6 text-red-500" /><span className="text-xl font-semibold">Negative News</span><Badge variant="secondary">{vendorData.negative_news.vendor_negative_news.length}</Badge></div>
                            </AccordionTrigger>
                            <AccordionContent className="px-6 pb-6">
                              <div className="space-y-4">
                                {vendorData.negative_news.vendor_negative_news.map((item: any, index: number) => (
                                  <motion.div key={index} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.1 }}>
                                    <Card className="p-4 border-l-4 border-red-500 hover:shadow-card-hover transition-all">
                                      <div className="flex items-start justify-between mb-2">
                                        <div className="flex-1"><h4 className="font-semibold">{item.title}</h4><Badge variant="outline" className="mt-1">{item.type}</Badge></div>
                                        <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">{item.date && new Date(item.date).toLocaleDateString()}</span>
                                      </div>
                                      <p className="text-sm text-muted-foreground mb-2">{item.summary}</p>
                                      {item.facts?.length > 0 && <ul className="text-xs text-gray-600 mb-2 list-disc list-inside">{item.facts.map((f: string, fi: number) => <li key={fi}>{f}</li>)}</ul>}
                                      <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline">Source: {item.source_url}</a>
                                    </Card>
                                  </motion.div>
                                ))}
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        )}
                      </Accordion>
                    </motion.div>
                  )}
                </motion.div>
              )}

              {/* ── STEP 3: Comparison ── */}
              {vendorData && !isSearchingVendor && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                  <Card className="glass-card p-8">
                    <div className="flex items-center justify-between mb-6">
                      <div><h2 className="text-2xl font-bold mb-2">Step 3: Document Comparison</h2><p className="text-muted-foreground">Compare protocol versions to identify changes</p></div>
                      <Badge className="bg-emerald-500 text-white"><CheckCircle2 className="h-4 w-4 mr-1" />Ready</Badge>
                    </div>
                    <div className="grid md:grid-cols-2 gap-6 mb-6">
                      <Card className="glass-card p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center"><FileText className="h-5 w-5 mr-2 text-primary" />Original Document</h3>
                        {!canReuploadFirst ? (
                          <div className="p-4 bg-primary/5 rounded-lg border-2 border-primary/20">
                            <div className="flex items-center justify-between mb-3">
                              <span className="text-sm font-medium">{uploadedProtocol?.name}</span>
                              <Badge variant="secondary">From Step 1</Badge>
                            </div>
                            <Button variant="outline" size="sm" className="w-full" onClick={() => setCanReuploadFirst(true)}><Upload className="h-4 w-4 mr-2" />Re-upload Different File</Button>
                          </div>
                        ) : (
                          <div {...reuploadDropzone.getRootProps()} className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${reuploadDropzone.isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary hover:bg-primary/5"}`}>
                            <input {...reuploadDropzone.getInputProps()} />
                            <Upload className="h-12 w-12 mx-auto mb-3 text-primary" />
                            <p className="text-sm text-muted-foreground">Drop new PDF or click to upload</p>
                          </div>
                        )}
                      </Card>
                      <Card className="glass-card p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center"><FileText className="h-5 w-5 mr-2 text-secondary" />Updated Document</h3>
                        <div {...secondDocDropzone.getRootProps()} className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${secondDocDropzone.isDragActive ? "border-secondary bg-secondary/5" : "border-border hover:border-secondary hover:bg-secondary/5"}`}>
                          <input {...secondDocDropzone.getInputProps()} />
                          <Upload className="h-12 w-12 mx-auto mb-3 text-secondary" />
                          {secondDocument ? <p className="text-sm font-medium">{secondDocument.name}</p> : <p className="text-sm text-muted-foreground">Drop PDF or click to upload</p>}
                        </div>
                      </Card>
                    </div>
                    <Button onClick={handleCompareDocuments} disabled={!uploadedProtocol || !secondDocument || isComparing} variant="gradient" className="w-full">
                      {isComparing ? "Comparing Documents..." : (<><GitCompare className="h-4 w-4 mr-2" />Run Comparative Analysis</>)}
                    </Button>
                  </Card>

                  {isComparing && (
                    <Card className="glass-card p-12">
                      <DocumentLoader file1={uploadedProtocol} file2={secondDocument}
                        onReset={() => { setIsComparing(false); setComparisonData(null); setSecondDocument(null); }}
                        onComplete={handleComparisonComplete}
                      />
                    </Card>
                  )}

                  {comparisonData && !isComparing && (() => {
                    console.log("[Step 3] Rendering comparison results, raw comparisonData:", comparisonData);
                    const parsedData = parseComparisonData(comparisonData);
                    console.log("[Step 3] Parsed comparison data for rendering:", parsedData);
                    return (
                      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 mt-6">
                        <Card className="glass-card p-6 mb-6">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-4">
                              <div><p className="text-sm text-muted-foreground">Original</p><p className="font-medium">{uploadedProtocol?.name}</p></div>
                              <ArrowRight className="h-5 w-5 text-muted-foreground" />
                              <div><p className="text-sm text-muted-foreground">Updated</p><p className="font-medium">{secondDocument?.name}</p></div>
                            </div>
                            <Badge className="bg-emerald-500 text-white">Analysis Complete</Badge>
                          </div>
                        </Card>
                        <Accordion type="multiple" defaultValue={["changes", "additions", "removals"]} className="space-y-4">
                          {parsedData.changes.length > 0 && (
                            <AccordionItem value="changes" className="glass-card border-0">
                              <AccordionTrigger className="px-6 py-4 hover:no-underline">
                                <div className="flex items-center space-x-3"><div className="h-3 w-3 rounded-full bg-yellow-400" /><span className="text-xl font-semibold">Changes</span><Badge variant="secondary">{parsedData.changes.length}</Badge></div>
                              </AccordionTrigger>
                              <AccordionContent className="px-6 pb-6">
                                <div className="space-y-4">
                                  {parsedData.changes.map((item, index) => (
                                    <motion.div key={index} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05 }}>
                                      <Card className="p-4 border-l-4 border-yellow-400">
                                        <div className="mb-3"><h4 className="font-semibold capitalize">{item.section}</h4>{item.subsection?.trim() && <p className="text-sm text-muted-foreground mt-1 capitalize">{item.subsection}</p>}</div>
                                        <div className="space-y-3">
                                          {item.addons.some(Boolean) && <div className="bg-blue-50 p-3 rounded border border-blue-200"><span className="text-xs font-semibold text-blue-700">Added:</span>{renderStringList(item.addons)}</div>}
                                          {item.impacts.some(Boolean) && <div className="bg-yellow-50 p-3 rounded border border-yellow-200"><span className="text-xs font-semibold text-yellow-700">Impact:</span>{renderStringList(item.impacts)}</div>}
                                          {item.removed.some(Boolean) && <div className="bg-red-50 p-3 rounded border border-red-200"><span className="text-xs font-semibold text-red-700">Removed:</span>{renderStringList(item.removed)}</div>}
                                        </div>
                                      </Card>
                                    </motion.div>
                                  ))}
                                </div>
                              </AccordionContent>
                            </AccordionItem>
                          )}
                          {parsedData.additions.length > 0 && (
                            <AccordionItem value="additions" className="glass-card border-0">
                              <AccordionTrigger className="px-6 py-4 hover:no-underline">
                                <div className="flex items-center space-x-3"><div className="h-3 w-3 rounded-full bg-emerald-500" /><span className="text-xl font-semibold">Additions</span><Badge variant="secondary">{parsedData.additions.length}</Badge></div>
                              </AccordionTrigger>
                              <AccordionContent className="px-6 pb-6">
                                <div className="space-y-4">{parsedData.additions.map((s, i) => renderSectionCard(s, i, "border-emerald-500", "bg-emerald-50/50", "text-emerald-700"))}</div>
                              </AccordionContent>
                            </AccordionItem>
                          )}
                          {parsedData.removals.length > 0 && (
                            <AccordionItem value="removals" className="glass-card border-0">
                              <AccordionTrigger className="px-6 py-4 hover:no-underline">
                                <div className="flex items-center space-x-3"><div className="h-3 w-3 rounded-full bg-red-500" /><span className="text-xl font-semibold">Removals</span><Badge variant="secondary">{parsedData.removals.length}</Badge></div>
                              </AccordionTrigger>
                              <AccordionContent className="px-6 pb-6">
                                <div className="space-y-4">{parsedData.removals.map((s, i) => renderSectionCard(s, i, "border-red-500", "bg-red-50/50", "text-red-700"))}</div>
                              </AccordionContent>
                            </AccordionItem>
                          )}
                          {parsedData.changes.length === 0 && parsedData.additions.length === 0 && parsedData.removals.length === 0 && (
                            <Card className="glass-card p-6"><p className="text-center text-muted-foreground">No differences found between documents</p></Card>
                          )}
                        </Accordion>
                      </motion.div>
                    );
                  })()}
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Global Citation Modal */}
      <CitationModal
        isOpen={!!citationModal}
        onClose={() => setCitationModal(null)}
        data={citationModal}
        fileName={citationFileName}
      />
    </div>
  );
}