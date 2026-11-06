import React from 'react';
import { FileText, Layers, Users, CheckSquare, FileCheck, FolderClock, Clock, CheckCircle2 } from 'lucide-react';

const STEPS = [
  { id: 1, title: '1. Convening Order', icon: FileText },
  { id: 2, title: '2. Supporting Docs', icon: Layers },
  { id: 3, title: '3. Witnesses', icon: Users },
  { id: 4, title: '4. Officer Review', icon: CheckSquare },
  { id: 5, title: '5. Draft Report', icon: FileCheck },
  { id: 6, title: 'All Cases', icon: FolderClock },
];

export default function StepTracker({ currentStep, onSelectStep, caseState }) {
  const isDrafted = caseState?.status === 'DRAFTED';

  return (
    <div className="bg-[#222816] border-b border-[#3a4324] shadow-xs">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between overflow-x-auto scrollbar-none">
        <div className="flex items-center gap-1">
          {STEPS.map((s) => {
            const Icon = s.icon;
            const isActive = currentStep === s.id;

            return (
              <button
                key={s.id}
                onClick={() => onSelectStep(s.id)}
                className={`flex items-center gap-2 py-3 px-3.5 text-xs font-medium border-b-2 transition whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'border-[#c23a2c] text-[#eef1d9] bg-[#2b3318]'
                    : 'border-transparent text-[#9aa67c] hover:text-[#dfe4c6] hover:bg-[#2e351c]'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-[#e0655a]' : 'text-[#848f68]'}`} />
                <span>{s.title}</span>
              </button>
            );
          })}
        </div>

        {/* Live Active Session Monitor Pill */}
        {caseState && currentStep !== 6 && (
          <div className="hidden md:flex items-center gap-2 py-1 px-3 bg-[#2b3218] border border-[#3c4526] rounded-full text-xs shrink-0">
            <span className="text-[#e0655a] font-mono font-medium text-[11px]">
              {caseState.case_id}
            </span>
            <span className="text-[#5a6442]">|</span>
            {isDrafted ? (
              <span className="flex items-center gap-1 text-[11px] font-medium text-white bg-[#5d7430] px-2 py-0.5 rounded-full shadow-xs">
                <CheckCircle2 className="w-3 h-3 text-white" />
                <span>Drafted</span>
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[11px] font-medium text-[#e0655a] bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                <Clock className="w-3 h-3 text-[#e0655a]" />
                <span>{caseState.status_label || 'Pending'}</span>
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
