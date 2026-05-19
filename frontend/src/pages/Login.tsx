import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import logoIcon from "@/assets/logo-icon.png";
import heroBg from "@/assets/hero-bg.jpg";
import { API_BASE_URL } from "@/config/api";

const Login = () => {
  const handleMicrosoftLogin = () => {
    window.location.href = `${API_BASE_URL}/auth/login`;
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{
        backgroundImage: `url(${heroBg})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {/* Dark overlay for readability */}
      <div className="absolute inset-0 bg-black/55 backdrop-blur-[2px]" />

      {/* Subtle floating orbs — replaces distracting particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute w-[500px] h-[500px] rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(99,179,237,0.08) 0%, transparent 70%)",
            top: "-120px",
            left: "-80px",
          }}
          animate={{ y: [0, 30, 0], x: [0, 15, 0] }}
          transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute w-[400px] h-[400px] rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(129,140,248,0.07) 0%, transparent 70%)",
            bottom: "-100px",
            right: "-60px",
          }}
          animate={{ y: [0, -25, 0], x: [0, -12, 0] }}
          transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: "easeOut" }}
        className="relative z-10 w-full max-w-sm px-4"
      >
        <div
          className="rounded-2xl p-8 space-y-7"
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.13)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            boxShadow:
              "0 8px 40px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.1)",
          }}
        >
          {/* Logo */}
          <div className="flex flex-col items-center gap-4">
            <div
              className="w-14 h-14 rounded-xl flex items-center justify-center"
              style={{
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.15)",
              }}
            >
              <img
                src={logoIcon}
                alt="Clinical Intelligence Platform"
                className="h-8 w-8 object-contain"
              />
            </div>

            <div className="text-center space-y-1.5">
              <h1
                className="text-2xl font-semibold tracking-tight text-white"
                style={{ letterSpacing: "-0.02em" }}
              >
                Clinical Trial Agent
              </h1>
              <p
                className="text-sm leading-relaxed"
                style={{ color: "rgba(255,255,255,0.5)" }}
              >
                AI-driven Protocol &amp; Vendor Intelligence
              </p>
            </div>
          </div>

          {/* Divider */}
          <div
            className="h-px w-full"
            style={{ background: "rgba(255,255,255,0.08)" }}
          />

          {/* Login action */}
          <div className="space-y-4">
            <motion.button
              onClick={handleMicrosoftLogin}
              whileHover={{ scale: 1.015 }}
              whileTap={{ scale: 0.985 }}
              className="w-full flex items-center justify-center gap-3 py-3 px-5 rounded-xl text-sm font-medium text-white transition-all duration-200"
              style={{
                background: "rgba(255,255,255,0.10)",
                border: "1px solid rgba(255,255,255,0.18)",
                boxShadow: "0 2px 12px rgba(0,0,0,0.2)",
                cursor: "pointer",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "rgba(255,255,255,0.16)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "rgba(255,255,255,0.10)";
              }}
            >
              {/* Microsoft logo */}
              <svg
                className="w-4 h-4 flex-shrink-0"
                viewBox="0 0 21 21"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect x="1" y="1" width="9" height="9" fill="#f25022" />
                <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
                <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
                <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
              </svg>
              Sign in with Microsoft
            </motion.button>

            <p
              className="text-center text-xs"
              style={{ color: "rgba(255,255,255,0.35)" }}
            >
              Secured via Azure Active Directory
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Login;