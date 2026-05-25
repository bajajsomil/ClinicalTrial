// components/ProtocalAnalyzerLoader.tsx

import React, { useState, useEffect, useRef } from 'react';
import { Activity, FileText, Search, Users, MapPin, Clock, AlertTriangle, CheckCircle2, Brain, Database, FileCheck, BarChart, Shield, ClipboardCheck, Microscope, TestTube } from 'lucide-react';

const ProtocolLoader = () => {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [activeMessages, setActiveMessages] = useState({ result1: 0, result2: 0 });

  // Track absolute start time so visibility catch-up works correctly
  const startTimeRef = useRef<number>(Date.now());
  const r1IndexRef = useRef<number>(0);
  const r2IndexRef = useRef<number>(0);
  const intervalRef1 = useRef<ReturnType<typeof setInterval> | null>(null);
  const intervalRef2 = useRef<ReturnType<typeof setInterval> | null>(null);

  const result1Messages = [
    { icon: Search, text: 'Finding key requirements...', color: 'from-blue-300 to-blue-400' },
    { icon: AlertTriangle, text: 'Analyzing risk factors...', color: 'from-purple-300 to-purple-400' },
    { icon: Clock, text: 'Finding trial duration...', color: 'from-pink-300 to-pink-400' },
    { icon: MapPin, text: 'Finding Number of sites...', color: 'from-rose-300 to-rose-400' },
    { icon: Users, text: 'Identifying Number of participants...', color: 'from-amber-300 to-amber-400' },
    { icon: MapPin, text: 'Identifying regions...', color: 'from-cyan-300 to-cyan-400' },
    { icon: Shield, text: 'Identifying required certifications...', color: 'from-violet-300 to-violet-400' },
  ];

  const result2Messages = [
    { icon: Users, text: 'Identifying participants...', color: 'from-green-300 to-green-400' },
    { icon: MapPin, text: 'Mapping trial regions...', color: 'from-teal-300 to-teal-400' },
    { icon: Activity, text: 'Validating endpoints...', color: 'from-indigo-300 to-indigo-400' },
    { icon: Database, text: 'Identifying Baseline...', color: 'from-emerald-300 to-emerald-400' },
    { icon: FileCheck, text: 'Identifying Blinding...', color: 'from-sky-300 to-sky-400' },
    { icon: Microscope, text: 'Identifying Dose Modifications...', color: 'from-fuchsia-300 to-fuchsia-400' },
    { icon: TestTube, text: 'Identifying Lab Assessments...', color: 'from-lime-300 to-lime-400' },
    { icon: ClipboardCheck, text: 'Finding phase details...', color: 'from-orange-300 to-orange-400' },
    { icon: BarChart, text: 'Analyzing Primary Endpoint...', color: 'from-slate-300 to-slate-400' },
    { icon: CheckCircle2, text: 'Analyzing Primary Objective...', color: 'from-red-300 to-red-400' },
    { icon: Activity, text: 'Finding Randomization details...', color: 'from-yellow-300 to-yellow-400' },
    { icon: Users, text: 'Identifying sample size details...', color: 'from-blue-300 to-blue-400' },
    { icon: Clock, text: 'Identifying screening period details...', color: 'from-purple-300 to-purple-400' },
    { icon: BarChart, text: 'Analyzing secondary endpoint...', color: 'from-pink-300 to-pink-400' },
    { icon: CheckCircle2, text: 'Analyzing secondary objective...', color: 'from-cyan-300 to-cyan-400' },
    { icon: FileText, text: 'Finding study type details...', color: 'from-violet-300 to-violet-400' },
    { icon: Users, text: 'Identifying target population...', color: 'from-rose-300 to-rose-400' },
    { icon: Clock, text: 'Finding treatment period details...', color: 'from-amber-300 to-amber-400' },
  ];

  // Step timings in ms
  const stepTimings = [0, 2000, 4000, 6000];
  const INTERVAL_MS = 2000;

  const computeStateFromElapsed = (elapsed: number) => {
    // Current step based on elapsed time
    let step = 0;
    for (let i = stepTimings.length - 1; i >= 0; i--) {
      if (elapsed >= stepTimings[i]) { step = i + 1; break; }
    }

    // Message indices: messages start cycling after 6000ms
    const messageElapsed = Math.max(0, elapsed - 6000);
    const r1 = Math.floor(messageElapsed / INTERVAL_MS);
    const r2 = Math.floor(messageElapsed / INTERVAL_MS);

    // Progress: 0 → 50% in first 6s, then +2% per interval tick
    const progressBase = elapsed >= 6000 ? 50 : (elapsed / 6000) * 50;
    const progressExtra = Math.min(50, r1 * 2);
    const prog = Math.min(100, progressBase + progressExtra);

    return { step, r1, r2, prog };
  };

  useEffect(() => {
    startTimeRef.current = Date.now();

    // Step timeouts driven by actual timestamps (not affected by throttling
    // because they fire once, and on return we catch up via visibilitychange)
    const stepTimeouts = stepTimings.map((timing, index) =>
      setTimeout(() => setCurrentStep(index + 1), timing)
    );

    setTimeout(() => setProgress(50), 6000);

    // Intervals for message cycling
    intervalRef1.current = setInterval(() => {
      r1IndexRef.current += 1;
      const idx = r1IndexRef.current % result1Messages.length;
      setActiveMessages(prev => ({ ...prev, result1: idx }));
      setProgress(prev => Math.min(100, prev + 2));
    }, INTERVAL_MS);

    intervalRef2.current = setInterval(() => {
      r2IndexRef.current += 1;
      const idx = r2IndexRef.current % result2Messages.length;
      setActiveMessages(prev => ({ ...prev, result2: idx }));
    }, INTERVAL_MS);

    return () => {
      if (intervalRef1.current) clearInterval(intervalRef1.current);
      if (intervalRef2.current) clearInterval(intervalRef2.current);
      stepTimeouts.forEach(t => clearTimeout(t));
    };
  }, []);

  // ── Visibility catch-up ───────────────────────────────────────────────────────
  // When the tab becomes visible again, compute how far along we should be
  // based on wall-clock time, and fast-forward all state at once.
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) return;

      const elapsed = Date.now() - startTimeRef.current;
      const { step, r1, r2, prog } = computeStateFromElapsed(elapsed);

      setCurrentStep(step);
      setProgress(prog);

      // Only update message indices if they've advanced
      if (r1 > r1IndexRef.current) {
        r1IndexRef.current = r1;
        setActiveMessages(prev => ({
          ...prev,
          result1: r1 % result1Messages.length,
        }));
      }
      if (r2 > r2IndexRef.current) {
        r2IndexRef.current = r2;
        setActiveMessages(prev => ({
          ...prev,
          result2: r2 % result2Messages.length,
        }));
      }

      // Restart intervals from now so they stay on schedule
      if (intervalRef1.current) clearInterval(intervalRef1.current);
      if (intervalRef2.current) clearInterval(intervalRef2.current);

      intervalRef1.current = setInterval(() => {
        r1IndexRef.current += 1;
        setActiveMessages(prev => ({ ...prev, result1: r1IndexRef.current % result1Messages.length }));
        setProgress(prev => Math.min(100, prev + 2));
      }, INTERVAL_MS);

      intervalRef2.current = setInterval(() => {
        r2IndexRef.current += 1;
        setActiveMessages(prev => ({ ...prev, result2: r2IndexRef.current % result2Messages.length }));
      }, INTERVAL_MS);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  return (
    <div className="py-8">
      <div className="mb-12">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Analysis Progress</span>
          <span className="text-sm font-medium text-gray-700">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-300 rounded-full"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      <div className="relative">
        <div className="flex justify-center mb-8">
          <div className={`flex flex-col items-center transform transition-all duration-1000 ${
            currentStep >= 1 ? 'scale-100 opacity-100' : 'scale-50 opacity-0'
          }`}>
            <div className="relative flex items-center justify-center">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-300 to-pink-300 rounded-full blur-xl opacity-50 animate-pulse"></div>
              <div className="relative bg-gradient-to-br from-purple-400 to-pink-400 rounded-full p-8 shadow-2xl flex items-center justify-center">
                <Brain className="w-12 h-12 text-white" />
              </div>
            </div>
            <p className="text-center mt-4 font-semibold text-gray-800">Orchestrator Agent</p>
          </div>
        </div>

        {currentStep >= 2 && (
          <div className="flex justify-center mb-4 animate-fadeIn">
            <svg width="40" height="80" viewBox="0 0 40 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 0 L20 70 M20 70 L10 60 M20 70 L30 60" stroke="#c084fc" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        )}

        {currentStep >= 2 && (
          <div className="flex justify-center mb-8 animate-fadeIn">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-300 to-cyan-300 rounded-2xl blur-lg opacity-50 animate-pulse"></div>
              <div className="relative bg-gradient-to-br from-blue-400 to-cyan-400 rounded-2xl p-6 shadow-xl">
                <FileText className="w-10 h-10 text-white mx-auto" />
                <p className="text-white font-semibold mt-2 text-center">Extracting Protocol Data</p>
              </div>
            </div>
          </div>
        )}

        {currentStep >= 3 && (
          <div className="flex justify-center gap-12 mb-4 animate-fadeIn">
            <svg width="40" height="80" viewBox="0 0 40 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 0 L20 70 M20 70 L10 60 M20 70 L30 60" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <svg width="40" height="80" viewBox="0 0 40 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 0 L20 70 M20 70 L10 60 M20 70 L30 60" stroke="#60a5fa" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        )}

        {currentStep >= 4 && (
          <div className="grid grid-cols-2 gap-4 max-w-4xl mx-auto animate-fadeIn">
            <div className="space-y-6">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-pink-300 to-rose-300 rounded-2xl blur-lg opacity-50 animate-pulse"></div>
                <div className="relative border-2 border-pink-300 shadow-xl bg-white rounded-lg">
                  <div className="p-4 border-b">
                    <h3 className="text-center text-lg font-semibold bg-gradient-to-r from-pink-500 to-rose-500 bg-clip-text text-transparent">
                      Analysing Criteria For Vendor Selection 
                    </h3>
                  </div>
                  <div className="p-4">
                    <div className="space-y-3 h-[200px] overflow-hidden relative">
                      {result1Messages
                        .slice(
                          Math.max(0, activeMessages.result1 - 1),
                          Math.min(result1Messages.length, activeMessages.result1 + 2)
                        )
                        .map((msg, idx) => {
                          const Icon = msg.icon;
                          const actualIdx = Math.max(0, activeMessages.result1 - 1) + idx;
                          const isActive = activeMessages.result1 === actualIdx;
                          const position = actualIdx - activeMessages.result1;
                          
                          return (
                            <div
                              key={actualIdx}
                              className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-500 ${
                                isActive
                                  ? `bg-gradient-to-r ${msg.color} text-white shadow-lg scale-100 z-10`
                                  : position < 0
                                  ? 'bg-gray-50 text-gray-500 scale-95 opacity-40'
                                  : 'bg-gray-50 text-gray-400 scale-95 opacity-40'
                              }`}
                              style={{
                                transform: `translateY(${(idx - (activeMessages.result1 > 0 ? 1 : 0)) * 64}px)`,
                                position: 'absolute',
                                width: 'calc(100% - 2rem)',
                                transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
                                top: '50%',
                                marginTop: '-24px'
                              }}
                            >
                              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'animate-pulse' : ''}`} />
                              <span className="text-sm font-medium">{msg.text}</span>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-green-300 to-teal-300 rounded-2xl blur-lg opacity-50 animate-pulse"></div>
                <div className="relative border-2 border-green-300 shadow-xl bg-white rounded-lg">
                  <div className="p-4 border-b">
                    <h3 className="text-center text-lg font-semibold bg-gradient-to-r from-green-500 to-teal-500 bg-clip-text text-transparent">
                      Protocol Analysis And Summarization
                    </h3>
                  </div>
                  <div className="p-4">
                    <div className="space-y-3 h-[200px] overflow-hidden relative">
                      {result2Messages
                        .slice(
                          Math.max(0, activeMessages.result2 - 1),
                          Math.min(result2Messages.length, activeMessages.result2 + 2)
                        )
                        .map((msg, idx) => {
                          const Icon = msg.icon;
                          const actualIdx = Math.max(0, activeMessages.result2 - 1) + idx;
                          const isActive = activeMessages.result2 === actualIdx;
                          const position = actualIdx - activeMessages.result2;
                          
                          return (
                            <div
                              key={actualIdx}
                              className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-500 ${
                                isActive
                                  ? `bg-gradient-to-r ${msg.color} text-white shadow-lg scale-100 z-10`
                                  : position < 0
                                  ? 'bg-gray-50 text-gray-500 scale-95 opacity-40'
                                  : 'bg-gray-50 text-gray-400 scale-95 opacity-40'
                              }`}
                              style={{
                                transform: `translateY(${(idx - (activeMessages.result2 > 0 ? 1 : 0)) * 64}px)`,
                                position: 'absolute',
                                width: 'calc(100% - 2rem)',
                                transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
                                top: '50%',
                                marginTop: '-24px'
                              }}
                            >
                              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'animate-pulse' : ''}`} />
                              <span className="text-sm font-medium">{msg.text}</span>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.8s ease-out;
        }
      `}</style>
    </div>
  );
};

export default ProtocolLoader;