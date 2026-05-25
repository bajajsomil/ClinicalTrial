import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getWsBaseUrl } from '@/config/api';
import {
  FileText,
  Check,
  CheckCircle,
  RotateCcw,
  Sparkles,
  AlertCircle,
  GitCompare,
  Scan,
  List,
  Layers,
  Type,
} from 'lucide-react';

const iconMap = {
  'scan': Scan,
  'check': Check,
  'list': List,
  'layers': Layers,
  'type': Type,
  'check-circle': CheckCircle,
  'git-compare': GitCompare,
  'file-text': FileText,
};

const DocumentLoader = ({ file1, file2, onReset, onComplete }) => {
  const [progress, setProgress] = useState(0);
  const [messages, setMessages] = useState([]);
  const [showResult, setShowResult] = useState(false);
  const [documentsSlideIn, setDocumentsSlideIn] = useState(false);
  const [highlightedSections, setHighlightedSections] = useState([]);
  const [error, setError] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const highlightTimers = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const stepMessageMap = {
    'extract_pages': 'Extracting pages from documents...',
    'extract_pages_complete': 'Pages extracted successfully',
    'identify_index': 'Identifying table of contents...',
    'identify_index_complete': 'Table of contents identified',
    'extract_sections': 'Extracting document sections...',
    'sections_extracted': 'Sections extracted successfully',
    'fill_sections': 'Analyzing section content...',
    'normalize_sections': 'Normalizing section headers...',
    'finalize': 'Finalizing comparison results...',
    'complete': 'Comparison complete!',
    'file1_received': 'File 1 uploaded successfully',
    'file2_received': 'File 2 uploaded successfully',
  };

  const getIconForStep = (step) => {
    const iconMap = {
      'extract_pages': 'scan',
      'extract_pages_complete': 'check',
      'identify_index': 'list',
      'identify_index_complete': 'check',
      'extract_sections': 'layers',
      'sections_extracted': 'check',
      'fill_sections': 'type',
      'normalize_sections': 'type',
      'finalize': 'sparkles',
      'complete': 'check-circle',
      'file1_received': 'check',
      'file2_received': 'check',
    };
    return iconMap[step] || 'git-compare';
  };

  useEffect(() => {
    setDocumentsSlideIn(true);

    // Connect to WebSocket
    // Base URL (ws:// or wss://) is derived automatically from VITE_API_BASE_URL
    const wsUrl = `${getWsBaseUrl()}/ws/compare-documents`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = async () => {
      console.log('WebSocket connected');

      try {
        // Send initial message with file names
        ws.send(JSON.stringify({
          type: 'start_comparison',
          file1_name: file1.name,
          file2_name: file2.name,
        }));

        // Send file1 as binary data
        const file1Buffer = await file1.arrayBuffer();
        ws.send(file1Buffer);

        // Send file2 as binary data
        const file2Buffer = await file2.arrayBuffer();
        ws.send(file2Buffer);

      } catch (err) {
        console.error('Error sending files:', err);
        setError('Failed to send files to server');
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
          // Update progress bar
          setProgress(data.progress || 0);

          // Add message to activity feed
          const message = {
            id: Date.now() + Math.random(),
            message: data.message || stepMessageMap[data.step] || data.step,
            type: data.step?.includes('complete') || data.step === 'complete' ? 'info' : 'process',
            icon: getIconForStep(data.step),
          };

          setMessages((prev) => [...prev, message]);

          // Highlight animation — track timer so it can be cancelled on tab re-focus
          setHighlightedSections((prev) => {
            const newSections = [...prev, Math.floor(Math.random() * 5)];
            const t = setTimeout(() => {
              setHighlightedSections((p) => p.slice(1));
            }, 1500);
            highlightTimers.current.push(t);
            return newSections;
          });
        } else if (data.type === 'data') {
          // Handle intermediate data updates
          const message = {
            id: Date.now() + Math.random(),
            message: data.message || 'Data received',
            type: 'info',
            icon: 'layers',
          };
          setMessages((prev) => [...prev, message]);
        } else if (data.type === 'complete') {
          // Comparison finished
          setProgress(100);
          setComparisonData(data.data);
          setShowResult(true);

          const message = {
            id: Date.now() + Math.random(),
            message: 'Comparison complete!',
            type: 'success',
            icon: 'check-circle',
          };
          setMessages((prev) => [...prev, message]);

          if (onComplete) {
            onComplete(data.data);
          }
        } else if (data.type === 'error') {
          setError(data.message);
          const message = {
            id: Date.now() + Math.random(),
            message: `Error: ${data.message}`,
            type: 'error',
            icon: 'alert',
          };
          setMessages((prev) => [...prev, message]);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error. Please try again.');
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [file1, file2, onComplete]);

  // ── Visibility catch-up ─────────────────────────────────────────────────────
  // When returning to the tab, flush any stale highlight timers and clear
  // highlighted sections so the visual state is consistent.
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) return;
      // Cancel all pending highlight-cleanup timers
      highlightTimers.current.forEach(t => clearTimeout(t));
      highlightTimers.current = [];
      // Clear all highlighted sections immediately
      setHighlightedSections([]);
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  if (showResult && comparisonData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 flex items-center justify-center p-6">
        <div className="max-w-4xl w-full p-10 bg-white rounded-2xl shadow-2xl">
          <div className="text-center space-y-6">
            <div className="flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-green-300 to-blue-300 rounded-full blur-xl opacity-50 animate-pulse"></div>
                <div className="relative bg-gradient-to-br from-green-100 to-blue-100 p-6 rounded-full">
                  <CheckCircle className="w-16 h-16 text-green-600" strokeWidth={1.5} />
                </div>
              </div>
            </div>

            <h2 className="text-4xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
              Comparison Complete!
            </h2>

            <div className="p-6 bg-blue-50 rounded-lg text-left max-h-64 overflow-y-auto border border-blue-200">
              <h3 className="font-semibold text-blue-900 mb-3">Comparison Results:</h3>
              <pre className="text-sm text-blue-800 whitespace-pre-wrap break-words font-mono">
                {JSON.stringify(comparisonData, null, 2)}
              </pre>
            </div>

            <button
              onClick={onReset}
              className="mt-6 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white px-8 py-5 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-2 font-semibold w-full"
            >
              <RotateCcw className="w-5 h-5" />
              New Comparison
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent flex items-center justify-center gap-2">
            <Sparkles className="w-8 h-8 text-purple-500 animate-pulse" />
            Comparing Documents...
          </h1>
          <p className="text-gray-500">AI agent analyzing differences</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 border-l-4 border-red-500 rounded">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Progress Bar */}
        <div className="p-6 bg-white rounded-lg shadow-lg border-0">
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-gray-600">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-purple-500 to-pink-500 h-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Documents Side by Side */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Document A */}
          <div
            className={`p-6 bg-white rounded-lg shadow-xl border-2 border-purple-200 transform transition-all duration-1000 ${documentsSlideIn ? 'translate-x-0 opacity-100' : '-translate-x-full opacity-0'
              }`}
          >
            <div className="space-y-4">
              <div className="flex items-center gap-3 pb-3 border-b border-blue-100">
                <FileText className="w-6 h-6 text-blue-500" />
                <h3 className="font-semibold text-blue-700 truncate" title={file1?.name}>
                  {file1?.name || 'Document A'}
                </h3>
              </div>
              <div className="space-y-2">
                {[0, 1, 2, 3, 4].map((index) => (
                  <div
                    key={index}
                    className={`h-4 bg-gradient-to-r from-blue-100 to-blue-50 rounded transition-all duration-500 ${highlightedSections.includes(index)
                        ? 'ring-2 ring-blue-400 shadow-lg scale-105'
                        : ''
                      }`}
                    style={{ width: `${60 + Math.random() * 40}%` }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Document B */}
          <div
            className={`p-6 bg-white rounded-lg shadow-xl border-2 border-cyan-200 transform transition-all duration-1000 ${documentsSlideIn ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
              }`}
          >
            <div className="space-y-4">
              <div className="flex items-center gap-3 pb-3 border-b border-pink-100">
                <FileText className="w-6 h-6 text-pink-500" />
                <h3 className="font-semibold text-blue-700 truncate" title={file1?.name}>
                  {file2?.name || 'Document B'}
                </h3>
              </div>
              <div className="space-y-2">
                {[0, 1, 2, 3, 4].map((index) => (
                  <div
                    key={index}
                    className={`h-4 bg-gradient-to-r from-cyan-100 to-cyan-50 rounded transition-all duration-500 ${highlightedSections.includes(index)
                        ? 'ring-2 ring-cyan-400 shadow-lg scale-105'
                        : ''
                      }`}
                    style={{ width: `${60 + Math.random() * 40}%` }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Comparison Messages from WebSocket */}
        <div className="p-6 bg-white rounded-lg shadow-lg border-0 max-h-96 overflow-y-auto">
          <h3 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-blue-500" />
            Comparison Activity
          </h3>
          <div className="space-y-2">
            {messages.length === 0 ? (
              <p className="text-sm text-gray-400 italic">Waiting for updates...</p>
            ) : (
              messages.map((msg, idx) => {
                const Icon = iconMap[msg.icon];
                const colorClass =
                  msg.type === 'error'
                    ? 'bg-red-50 border-red-200 text-red-700'
                    : msg.type === 'success'
                      ? 'bg-green-50 border-green-200 text-green-700'
                      : msg.type === 'info'
                        ? 'bg-blue-50 border-blue-200 text-blue-700'
                        : 'bg-gray-50 border-gray-200 text-gray-700';

                return (
                  <div
                    key={msg.id}
                    className={`p-3 rounded-lg border-l-4 ${colorClass} animate-in fade-in duration-500`}
                    style={{ animationDelay: `${idx * 50}ms` }}
                  >
                    <div className="flex items-center gap-3">
                      {Icon && <Icon className="w-4 h-4 flex-shrink-0" />}
                      <span className="text-sm font-medium">{msg.message}</span>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentLoader;