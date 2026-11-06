import React, { useState, useEffect } from 'react';
import { 
  FolderClock, 
  FileText, 
  Users, 
  Layers, 
  Trash2, 
  ArrowRight, 
  PlusCircle, 
  CheckCircle2, 
  Clock, 
  RefreshCw, 
  Search,
  CheckCircle,
  Shield
} from 'lucide-react';

export default function AllCasesView({ onSelectCase, onNewCase }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL' | 'DRAFTED' | 'PENDING'
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/cases');
      if (res.ok) {
        const data = await res.json();
        setCases(data.cases || []);
      }
    } catch (err) {
      console.error('Error fetching cases:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLoad = async (caseId) => {
    setActionLoading(true);
    try {
      const res = await fetch(`/api/cases/${caseId}/load`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        onSelectCase(data.case);
      }
    } catch (err) {
      console.error('Error loading case:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (caseId, e) => {
    e.stopPropagation();
    if (window.confirm(`Are you sure you want to permanently delete case record "${caseId}"?`)) {
      try {
        const res = await fetch(`/api/cases/${caseId}`, { method: 'DELETE' });
        if (res.ok) {
          const data = await res.json();
          setCases(data.cases || []);
        }
      } catch (err) {
        console.error('Error deleting case:', err);
      }
    }
  };

  const filteredCases = cases.filter((c) => {
    if (statusFilter === 'DRAFTED' && c.status !== 'DRAFTED') return false;
    if (statusFilter === 'PENDING' && c.status === 'DRAFTED') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = (c.case_id || '').toLowerCase().includes(q);
      const matchSubject = (c.subject || '').toLowerCase().includes(q);
      const matchAuth = (c.authority || '').toLowerCase().includes(q);
      const matchStatus = (c.status_label || '').toLowerCase().includes(q);
      return matchId || matchSubject || matchAuth || matchStatus;
    }
    return true;
  });

  const totalCount = cases.length;
  const draftedCount = cases.filter((c) => c.status === 'DRAFTED').length;
  const pendingCount = cases.filter((c) => c.status !== 'DRAFTED').length;

  return (
    <div className="space-y-5 font-sans">
      {/* Top Banner */}
      <div className="bg-white p-5 rounded-xl border border-[#3c4526] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#edf0d9]">All Court of Inquiry Records</h2>
            <span className="text-xs bg-[#2c3319] text-[#a9bd77] border border-[#39421f] px-2.5 py-0.5 rounded-full font-medium">
              {totalCount} Total
            </span>
          </div>
          <p className="text-xs text-[#b2bc94] mt-0.5">
            Every inquiry session is tracked, recorded, and archived here with real-time status.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchCases}
            className="p-2 text-[#b2bc94] hover:text-[#edf0d9] hover:bg-[#2c3319] rounded-lg transition cursor-pointer"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={onNewCase}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Start New Inquiry</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-3 rounded-xl border border-[#3c4526] flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xs">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 w-full sm:w-auto">
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 ${
              statusFilter === 'ALL'
                ? 'bg-[#5d7430] text-white shadow-xs'
                : 'text-[#b2bc94] hover:bg-[#272e17]'
            }`}
          >
            <span>All Inquiries</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              statusFilter === 'ALL' ? 'bg-[#3d4a24] text-white' : 'bg-[#2c3319] text-[#b2bc94]'
            }`}>
              {totalCount}
            </span>
          </button>

          <button
            onClick={() => setStatusFilter('DRAFTED')}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 ${
              statusFilter === 'DRAFTED'
                ? 'bg-[#5d7430] text-white shadow-xs'
                : 'text-[#b2bc94] hover:bg-[#272e17]'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Drafted</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              statusFilter === 'DRAFTED' ? 'bg-[#4f6129] text-white' : 'bg-[#2c3319] text-[#a9bd77]'
            }`}>
              {draftedCount}
            </span>
          </button>

          <button
            onClick={() => setStatusFilter('PENDING')}
            className={`px-3 py-1.5 text-xs rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5 ${
              statusFilter === 'PENDING'
                ? 'bg-[#b33324] text-white shadow-xs'
                : 'text-[#b2bc94] hover:bg-[#272e17]'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Pending</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
              statusFilter === 'PENDING' ? 'bg-[#bd3527] text-white' : 'bg-red-50 text-[#e0655a]'
            }`}>
              {pendingCount}
            </span>
          </button>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#7a8560]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by ID, subject, status..."
            className="w-full bg-[#272e17] border border-[#3c4526] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[#edf0d9] placeholder-[#717c58] focus:bg-white focus:border-[#7d9440] focus:outline-none transition"
          />
        </div>
      </div>

      {/* Cases Grid */}
      {loading ? (
        <div className="bg-white p-12 text-center rounded-xl border border-[#3c4526]">
          <RefreshCw className="w-6 h-6 animate-spin text-[#a9bd77] mx-auto mb-2" />
          <span className="text-xs text-[#98a477]">Loading cases directory...</span>
        </div>
      ) : filteredCases.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCases.map((c) => {
            const isDrafted = c.status === 'DRAFTED';

            return (
              <div
                key={c.case_id}
                onClick={() => handleLoad(c.case_id)}
                className={`bg-white p-5 rounded-xl border transition cursor-pointer flex flex-col justify-between shadow-xs hover:border-[#7d9440] group ${
                  c.is_active ? 'border-[#7d9440] ring-2 ring-[#7d9440]/20' : 'border-[#3c4526]'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-2.5">
                    <span className="font-mono font-medium text-[#edf0d9] bg-[#272e17] px-2 py-0.5 rounded border border-[#333b21]">
                      {c.case_id}
                    </span>

                    <div className="flex items-center gap-1.5">
                      {/* Status Badge */}
                      {isDrafted ? (
                        <span className="flex items-center gap-1 text-[11px] font-medium bg-[#2c3319] text-[#a9bd77] border border-[#39421f] px-2.5 py-0.5 rounded-full">
                          <CheckCircle2 className="w-3 h-3 text-[#a9bd77]" />
                          <span>Drafted</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[11px] font-medium bg-red-50 text-[#e0655a] border border-red-200 px-2.5 py-0.5 rounded-full">
                          <Clock className="w-3 h-3 text-[#e0655a]" />
                          <span>{c.status_label || 'Pending'}</span>
                        </span>
                      )}

                      {c.is_active && (
                        <span className="text-[10px] bg-[#5d7430] text-white px-2 py-0.5 rounded-full font-medium">
                          Active
                        </span>
                      )}
                    </div>
                  </div>

                  <h3 className="font-semibold text-[#edf0d9] text-sm line-clamp-2 mb-1 group-hover:text-[#a9bd77] transition">
                    {c.subject}
                  </h3>

                  <div className="text-xs text-[#b2bc94] mb-3 flex items-center justify-between">
                    <span>Authority: <strong className="text-[#edf0d9] font-medium">{c.authority}</strong></span>
                    <span className="text-[11px] text-[#98a477]">{c.created_at}</span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-[#b2bc94] pt-3 border-t border-[#2f3619]">
                    <span className="flex items-center gap-1 font-normal">
                      <Layers className="w-3.5 h-3.5 text-[#848f68]" />
                      <span>{c.docs_count} Exhibits</span>
                    </span>
                    <span className="flex items-center gap-1 font-normal">
                      <Users className="w-3.5 h-3.5 text-[#848f68]" />
                      <span>{c.witnesses_count} Witnesses</span>
                    </span>
                    {isDrafted && (
                      <span className="flex items-center gap-1 text-[#a9bd77] font-medium ml-auto">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>IAFD-931 Ready</span>
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 mt-3 border-t border-[#2f3619]">
                  <button
                    onClick={(e) => handleDelete(c.case_id, e)}
                    className="p-1.5 text-[#848f68] hover:text-[#e0655a] hover:bg-red-50 rounded-lg transition cursor-pointer"
                    title="Delete inquiry record"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <div className="flex items-center gap-1 text-xs font-medium text-[#a9bd77] group-hover:translate-x-0.5 transition">
                    <span>{c.is_active ? 'Continue Inquiry' : 'Open Inquiry'}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white p-16 text-center rounded-xl border border-dashed border-[#3c4526]">
          <FolderClock className="w-10 h-10 text-[#8b9771] mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-[#edf0d9]">No Inquiries Found</h3>
          <p className="text-xs text-[#98a477] mt-1 max-w-sm mx-auto">
            {searchQuery 
              ? `No inquiries match your query "${searchQuery}".` 
              : statusFilter !== 'ALL' 
                ? `No inquiry records currently in '${statusFilter}' status.`
                : "You haven't initiated any inquiries yet. Click below to start your first Court of Inquiry."
            }
          </p>
          <button
            onClick={onNewCase}
            className="mt-4 px-4 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs inline-flex items-center gap-1.5"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Start New Inquiry</span>
          </button>
        </div>
      )}
    </div>
  );
}
