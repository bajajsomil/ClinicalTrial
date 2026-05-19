// components/VendorIntelligenceLoader.tsx

import React, { useState, useEffect } from 'react';
import { Search, Beaker, FileText, ClipboardCheck, TestTube, Activity, Database } from 'lucide-react';
 
const VendorIntelligenceLoader = ({ 
  message, 
  vendorName, 
  vendorCategory,
  apiResponseReceived = false,
  onComplete
}: { 
  message: string;
  vendorName: string;
  vendorCategory: string;
  apiResponseReceived?: boolean;
  onComplete?: () => void;
}) => {  
  const [stage, setStage] = useState('idle');
  const [currentSearch, setCurrentSearch] = useState(0);
  const [typedText, setTypedText] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showComponents, setShowComponents] = useState(true);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);
  const [waitingForApi, setWaitingForApi] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState(Date.now()); // ADD THIS
 
  const currentYear = new Date().getFullYear();
  const startYear = currentYear - 1;
  const endYear = currentYear;

  const searches = [
    // Capabilities
    { text: `What ${vendorName} offers in ${vendorCategory} services and capabilities`, type: "capability" },
    { text: `What solutions does ${vendorName} provide in the ${vendorCategory} domain`, type: "capability" },
    { text: `What technologies, platforms, or methods does ${vendorName} use in ${vendorCategory}`, type: "capability" },
    { text: `How does ${vendorName} differentiate itself in ${vendorCategory} compared to competitors`, type: "capability" },
    { text: `What global presence, infrastructure, or resources does ${vendorName} have in ${vendorCategory}`, type: "capability" },
    
    // Positive News
    { text: `Recent partnerships or collaborations of ${vendorName} from ${startYear} to ${endYear}`, type: "positive" },
    { text: `Awards or recognitions received by ${vendorName} from ${startYear} to ${endYear}`, type: "positive" },
    { text: `New services, innovations, or expansions by ${vendorName} from ${startYear} to ${endYear}`, type: "positive" },
    { text: `Positive contributions or achievements of ${vendorName} from ${startYear} to ${endYear}`, type: "positive" },
    { text: `Financial or market performance updates of ${vendorName} from ${startYear} to ${endYear}`, type: "positive" },
    
    // Negative News
    { text: `Recent controversies or criticisms of ${vendorName} from ${startYear} to ${endYear}`, type: "negative" },
    { text: `Lawsuits, regulatory issues, or compliance challenges faced by ${vendorName} from ${startYear} to ${endYear}`, type: "negative" },
    { text: `Negative client or customer feedback about ${vendorName} from ${startYear} to ${endYear}`, type: "negative" },
    { text: `Service disruptions, delays, or operational issues related to ${vendorName} from ${startYear} to ${endYear}`, type: "negative" },
    { text: `Financial, staffing, or organizational challenges reported by ${vendorName} from ${startYear} to ${endYear}`, type: "negative" }
  ];
 
  const components = [
    { icon: Beaker, label: "Lab Equipment", rotation: -15, top: '2%', left: '6%', color: 'from-pink-200 to-pink-300', iconColor: 'text-pink-600' },
    { icon: TestTube, label: "Testing", rotation: 10, top: '4%', left: '80%', color: 'from-blue-200 to-blue-300', iconColor: 'text-blue-600' },
    { icon: ClipboardCheck, label: "Compliance", rotation: -8, top: '60%', left: '7%', color: 'from-green-200 to-green-300', iconColor: 'text-green-600' },
    { icon: FileText, label: "Documentation", rotation: 12, top: '72%', left: '70%', color: 'from-yellow-200 to-yellow-300', iconColor: 'text-yellow-600' },
    { icon: Activity, label: "Monitoring", rotation: -12, top: '8%', left: '45%', color: 'from-purple-200 to-purple-300', iconColor: 'text-purple-600' },
    { icon: Database, label: "Data Storage", rotation: 8, top: '70%', left: '40%', color: 'from-orange-200 to-orange-300', iconColor: 'text-orange-600' }
  ];

  // Monitor API response and adjust speed
  useEffect(() => {
    if (apiResponseReceived && currentSearch < searches.length - 1 && speedMultiplier === 1) {
      setSpeedMultiplier(2); // Speed up to 2x after API response
    }
  }, [apiResponseReceived, currentSearch, speedMultiplier]);
  
  // Auto-start the search when component mounts
  useEffect(() => {
    startSearch();
  }, []);
 
  useEffect(() => {
    if (stage === 'typing') {
      const fullText = searches[currentSearch].text;
      if (typedText.length < fullText.length) {
        const timeout = setTimeout(() => {
          setTypedText(fullText.slice(0, typedText.length + 1));
          setLastUpdateTime(Date.now()); // ADD THIS
        }, 80 / speedMultiplier);
        return () => clearTimeout(timeout);
      } else {
        const timeout = setTimeout(() => {
          setStage('clicking');
          setLastUpdateTime(Date.now()); // ADD THIS
        }, 500 / speedMultiplier);
        return () => clearTimeout(timeout);
      }
    }
  }, [stage, typedText, currentSearch, speedMultiplier]);
 
  useEffect(() => {
    if (stage === 'clicking') {
      setTimeout(() => {
        setShowComponents(false);
        setStage('searching');
      }, 500 / speedMultiplier);
    }
  }, [stage, speedMultiplier]);
 
  useEffect(() => {
    if (stage === 'searching') {
      setTimeout(() => {
        setStage('storing');
        const result = {
          query: searches[currentSearch].text,
          type: searches[currentSearch].type,
          timestamp: Date.now()
        };
        setSearchResults(prev => [...prev, result]);
      }, 2500 / speedMultiplier);
    }
  }, [stage, speedMultiplier]);
 
  useEffect(() => {
    if (stage === 'storing') {
      setTimeout(() => {
        if (currentSearch < searches.length - 1) {
          setCurrentSearch(currentSearch + 1);
          setTypedText('');
          setShowComponents(true);
          setStage('typing');
        } else {
          // Reached the last step (step 15)
          if (apiResponseReceived) {
            // API response received, complete immediately
            setStage('complete');
            if (onComplete) onComplete();
          } else {
            // Wait for API response at step 15
            setWaitingForApi(true);
          }
        }
      }, 1000 / speedMultiplier);
    }
  }, [stage, currentSearch, apiResponseReceived, speedMultiplier]);

  // Handle completion when API response arrives while waiting
  useEffect(() => {
    if (waitingForApi && apiResponseReceived) {
      setWaitingForApi(false);
      setStage('complete');
      if (onComplete) onComplete();
    }
  }, [waitingForApi, apiResponseReceived]);
  

  // ADD THIS: Handle visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Tab became visible again
        setLastUpdateTime(Date.now());
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);
  const startSearch = () => {
    setStage('typing');
    setCurrentSearch(0);
    setTypedText('');
    setSearchResults([]);
    setShowComponents(true);
    setSpeedMultiplier(1);
    setWaitingForApi(false);
  };
 
  const getResultsByType = (type) => {
    return searchResults.filter(r => r.type === type).length;
  };
 
  return (
  <div className="flex items-center justify-center py-12">
    <div className="w-full max-w-6xl">
       
 
        {stage !== 'idle' && stage !== 'complete' && (
          <div className="relative" style={{ height: '700px' }}>

            {/* Status Text */}
            <div className="absolute top-8 left-1/2 -translate-x-1/2 text-center w-full px-4">
              <p className="text-xl font-semibold text-gray-700 mb-1">
                AI Vendor Search Agent
              </p>
              <p className="text-sm text-gray-500 mb-2">
                {waitingForApi 
                  ? 'Processing results... Please wait' 
                  : 'Scanning global sources for vendor ...'}
              </p>
              {stage !== 'idle' && (
                <div className="inline-flex items-center gap-2 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-full shadow-md">
                  <span className="text-xs font-medium text-gray-600">Current Focus:</span>
                  <span className={`text-xs font-bold ${
                    searches[currentSearch]?.type === 'capability' ? 'text-blue-600' :
                    searches[currentSearch]?.type === 'positive' ? 'text-green-600' :
                    'text-red-600'
                  }`}>
                    {searches[currentSearch]?.type === 'capability' ? 'Capabilities' :
                    searches[currentSearch]?.type === 'positive' ? 'Positive News' :
                    'Negative News'}
                  </span>
                </div>
              )}
            </div>
            {/* Tablet Device */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
              {/* Tablet Frame */}
              <div className="relative bg-gradient-to-br from-gray-800 to-gray-900 rounded-3xl p-3 shadow-2xl" style={{ width: '700px', height: '450px' }}>


                {/* Camera */}
                <div className="absolute top-3 left-1/2 -translate-x-1/2 w-2 h-2 bg-gray-700 rounded-full"></div>
                
                {/* Screen Content */}
                <div className="w-full h-full bg-white rounded-2xl relative overflow-hidden">
                  {/* Floating Components */}
                  {showComponents && components.map((comp, idx) => (
                    <div
                      key={idx}
                      className="absolute animate-float-in"
                      style={{
                        top: comp.top,
                        left: comp.left,
                        animationDelay: `${idx * 0.15}s`,
                        transform: `rotate(${comp.rotation}deg)`
                      }}
                    >
                      <div className={`bg-gradient-to-br ${comp.color} p-4 rounded-2xl shadow-lg transform hover:scale-110 transition-transform`}>
                        <comp.icon className={`w-8 h-8 ${comp.iconColor}`} />
                        <p className="text-xs mt-2 text-gray-700 font-medium">{comp.label}</p>
                      </div>
                    </div>
                  ))}

                  {/* Search Bar - Only when components are visible */}
                  {showComponents && !waitingForApi && (
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse-slow">
                      <div className="bg-white rounded-full shadow-2xl p-3 flex items-center gap-3" style={{ width: '580px' }}>
                        <input
                          type="text"
                          value={typedText}
                          readOnly
                          placeholder="Search vendor information..."
                          className="flex-1 px-4 py-2 text-gray-700 bg-transparent outline-none"
                        />
                        <button
                          className={`p-3 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 text-white transition-all duration-300 ${
                            stage === 'clicking' ? 'scale-90' : 'scale-100'
                          }`}
                        >
                          <Search className="w-5 h-5" />
                        </button>
                      </div>
                      <div className="mt-2 text-center">
                        <span className="text-xs text-purple-600 font-semibold">
                          Search {currentSearch + 1} of {searches.length}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Waiting for API Animation */}
                  {waitingForApi && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50">
                      <div className="text-center space-y-6">
                        <div className="relative">
                          <div className="w-24 h-24 border-8 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>
                          <Database className="w-12 h-12 text-blue-600 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                        </div>
                        <div className="space-y-2">
                          <p className="text-lg font-semibold text-gray-800">Processing Results...</p>
                          <p className="text-sm text-gray-600">Waiting for API response</p>
                          <div className="flex gap-2 justify-center">
                            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                            <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Searching Animation */}
                  {stage === 'searching' && !waitingForApi && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white">
                      <div className="text-center space-y-6">
                        <div className="relative">
                          <div className="w-24 h-24 border-8 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto"></div>
                          <Search className="w-12 h-12 text-indigo-600 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                        </div>
                        <div className="space-y-2">
                          <p className="text-lg font-semibold text-gray-800">Searching the Internet...</p>
                          <div className="flex gap-2 justify-center">
                            <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
                            <div className="w-2 h-2 bg-violet-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            <div className="w-2 h-2 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Storing Animation */}
                  {stage === 'storing' && !waitingForApi && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-green-100 to-emerald-100">
                      <div className="text-center space-y-4">
                        <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto animate-bounce">
                          <Database className="w-10 h-10 text-white" />
                        </div>
                        <p className="text-lg font-semibold text-gray-800">Results Stored!</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
 
            {/* Progress Indicator */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur-sm rounded-full px-8 py-3 shadow-lg">
              <div className="flex gap-2">
                {searches.map((_, idx) => (
                  <div
                    key={idx}
                    className={`w-3 h-3 rounded-full transition-all duration-300 ${
                      idx < currentSearch ? 'bg-green-500' :
                      idx === currentSearch ? waitingForApi ? 'bg-blue-500 animate-pulse' : 'bg-indigo-500 animate-pulse' :
                      'bg-gray-300'
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
 
        {stage === 'complete' && (
          <div className="space-y-8 animate-fade-in">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full flex items-center justify-center mx-auto">
                <ClipboardCheck className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-4xl font-bold text-gray-800">Search Complete!</h2>
              <p className="text-gray-600">Analyzed {searches.length} data sources</p>
            </div>
 
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-white rounded-3xl p-8 shadow-xl border-t-4 border-blue-500 transform hover:scale-105 transition-transform">
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
                    <Activity className="w-8 h-8 text-blue-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800">Capabilities</h3>
                  <p className="text-5xl font-bold text-blue-600">{getResultsByType('capability')}</p>
                  <p className="text-sm text-gray-600">findings</p>
                </div>
              </div>
 
              <div className="bg-white rounded-3xl p-8 shadow-xl border-t-4 border-green-500 transform hover:scale-105 transition-transform">
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                    <ClipboardCheck className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800">Positive News</h3>
                  <p className="text-5xl font-bold text-green-600">{getResultsByType('positive')}</p>
                  <p className="text-sm text-gray-600">findings</p>
                </div>
              </div>
 
              <div className="bg-white rounded-3xl p-8 shadow-xl border-t-4 border-red-500 transform hover:scale-105 transition-transform">
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                    <FileText className="w-8 h-8 text-red-600" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-800">Negative News</h3>
                  <p className="text-5xl font-bold text-red-600">{getResultsByType('negative')}</p>
                  <p className="text-sm text-gray-600">findings</p>
                </div>
              </div>
            </div>
 
          </div>
        )}
      </div>
 
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(var(--rotation)); }
          50% { transform: translateY(-20px) rotate(var(--rotation)); }
        }
        @keyframes float-in {
          0% {
            opacity: 0;
            transform: scale(0) rotate(180deg);
          }
          60% {
            transform: scale(1.1) rotate(-10deg);
          }
          100% {
            opacity: 1;
            transform: scale(1) rotate(0deg);
          }
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-float {
          animation: float 3s ease-in-out infinite;
        }
        .animate-float-in {
          animation: float-in 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards, float 3s ease-in-out infinite 0.6s;
        }
        .animate-fade-in {
          animation: fade-in 0.8s ease-out;
        }
        .animate-pulse-slow {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
      `}</style>
    </div>
  );
};
 
export default VendorIntelligenceLoader;