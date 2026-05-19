// components/Navbar.tsx

import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import logoIcon from "@/assets/logo-icon.png";

const Navbar = () => {
  const location = useLocation();
  
  const links = [
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass-card border-b border-primary/20">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3 group">
            <img src={logoIcon} alt="Clinical Intelligence Platform" className="h-10 w-15 transition-transform group-hover:scale-110" />
            <span className="text-xl font-semibold gradient-text">Clinical Trial Agent</span>
          </Link>
          
          <div className="flex items-center space-x-8">
            {links.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className="relative py-2 text-sm font-medium transition-colors hover:text-primary"
              >
                <span className={location.pathname === link.path ? "text-primary" : "text-foreground"}>
                  {link.name}
                </span>
                {location.pathname === link.path && (
                  <motion.div
                    layoutId="navbar-indicator"
                    className="absolute -bottom-1 left-0 right-0 h-0.5 bg-gradient-primary"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
