import React from 'react';
import { LogOut, RotateCcw, FolderClock, Shield } from 'lucide-react';

export default function Navbar({ onLogout, onResetCase, onOpenCases }) {
  return (
    <header className="bg-[#10140a] border-b border-[#c23a2c] sticky top-0 z-50 shadow-xs">
      <div className="h-0.5 bg-[#b33324] w-full" />
      
      <div className="max-w-6xl mx-auto px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 flex items-center justify-center shrink-0">
            <img
              src="/army-logo.png"
              alt="Army Logo"
              className="w-full h-full object-contain"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = '/image.png';
              }}
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-[#e9ecd4] leading-tight">
                Court of Inquiry Generation
              </h1>
              <span className="text-[10px] font-medium uppercase tracking-wider bg-[#b33324] text-white px-2 py-0.5 rounded">
                Army Legal
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {onOpenCases && (
            <button
              onClick={onOpenCases}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white hover:text-white bg-[#252c16] hover:bg-[#333c1f] border border-[#3d4726] rounded-lg transition cursor-pointer font-medium"
              title="View all saved inquiry records"
            >
              <FolderClock className="w-3.5 h-3.5 text-[#e9ecd4]" />
              <span>All Cases</span>
            </button>
          )}

          {onResetCase && (
            <button
              onClick={onResetCase}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#e9ecd4] hover:text-white hover:bg-[#252c16] rounded-lg transition cursor-pointer font-medium"
              title="Start a new inquiry"
            >
              <RotateCcw className="w-3.5 h-3.5 text-[#e0655a]" />
              <span>New Case</span>
            </button>
          )}

          <div className="text-xs font-medium text-white px-2.5 py-1 bg-[#b33324] rounded-md shadow-xs flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <span>Admin</span>
          </div>

          <button
            onClick={onLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#e9ecd4] hover:text-white bg-transparent hover:bg-[#b33324] border border-[#3d4726] hover:border-[#c94032] rounded-lg transition cursor-pointer font-medium"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
