import React, { useState, useEffect } from 'react';
import { 
  Download, 
  Printer, 
  RefreshCw, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight, 
  FolderClock,
  ShieldAlert,
  FileCheck2,
  Award
} from 'lucide-react';

export default function CoiDraftStep({ caseState, onUpdateCase, onPrevStep, onViewAllCases }) {
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState(caseState?.coi_draft);
  const [errorMsg, setErrorMsg] = useState('');

  // Sync draft whenever caseState updates
  useEffect(() => {
    if (caseState?.coi_draft) {
      setDraft(caseState.coi_draft);
    }
  }, [caseState?.coi_draft]);

  // If no draft exists or findings are empty, trigger generation
  useEffect(() => {
    const isDraftIncomplete = !draft || !draft.findings_of_the_court || draft.findings_of_the_court.length === 0;
    if (isDraftIncomplete && !loading) {
      handleGenerateDraft();
    }
  }, []);

  const handleGenerateDraft = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch('/api/coi/generate', { method: 'POST' });
      const data = await res.json();
      if (data.success && data.coi_draft) {
        setDraft(data.coi_draft);
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
      } else {
        setErrorMsg('Could not assemble draft. Please ensure Convening Order is uploaded.');
      }
    } catch (err) {
      console.error('Error generating CoI draft:', err);
      setErrorMsg(`Failed to generate draft: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadDocx = () => {
    window.open('/api/coi/download-docx', '_blank');
  };

  const handlePrint = () => {
    window.print();
  };

  const header = draft?.header || {};
  const comp = header?.composition_of_court || [];
  const witnesses = draft?.witness_proceedings || [];
  const findings = draft?.findings_of_the_court || [];
  const opinions = draft?.opinion_of_the_court || [];
  const remarks = draft?.remarks_of_convening_authority || {};
  const sigs = draft?.signatures || {};

  const hasDraftContent = draft && findings.length > 0;

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white p-5 rounded-xl border border-[#3c4526] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs print:hidden">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#edf0d9]">5. Court of Inquiry Proceedings Draft</h2>
          </div>
          <p className="text-xs text-[#b2bc94] mt-0.5">
            Standard Armed Forces statutory proceedings format matching the official Court of Inquiry format.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleGenerateDraft}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#272e17] hover:bg-[#2c3319] text-[#d7debc] border border-[#3c4526] rounded-lg text-xs font-medium transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#a9bd77]' : ''}`} />
            <span>{loading ? 'Synthesizing...' : 'Regenerate Draft'}</span>
          </button>

          <button
            onClick={handlePrint}
            disabled={!hasDraftContent}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#272e17] hover:bg-[#2c3319] text-[#d7debc] border border-[#3c4526] rounded-lg text-xs font-medium transition cursor-pointer disabled:opacity-50"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print</span>
          </button>

          <button
            onClick={handleDownloadDocx}
            disabled={!hasDraftContent}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download DOCX</span>
          </button>
        </div>
      </div>

      {/* Drafted & Monitored Status Banner */}
      {hasDraftContent && !loading && (
        <div className="bg-[#2c3319] border border-[#39421f] text-[#d7debc] p-4 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs print:hidden">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#5d7430] text-white flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-medium uppercase tracking-wider bg-[#5d7430] text-white px-2 py-0.5 rounded shadow-xs">
                  Status: Drafted
                </span>
                <span className="text-xs font-medium text-[#edf0d9]">Recorded in All Cases Tab</span>
              </div>
              <p className="text-xs text-[#b2bc94] mt-0.5">
                Inquiry case <strong>{caseState?.case_id}</strong> is monitored and archived. You can export or reload it anytime from the All Cases tab.
              </p>
            </div>
          </div>
          {onViewAllCases && (
            <button
              onClick={onViewAllCases}
              className="px-3.5 py-1.5 bg-white border border-[#7d9440] hover:bg-[#2c3319] text-[#a9bd77] text-xs font-medium rounded-lg transition cursor-pointer shrink-0 shadow-xs flex items-center gap-1.5"
            >
              <FolderClock className="w-3.5 h-3.5 text-[#a9bd77]" />
              <span>View in All Cases</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2 print:hidden font-medium">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="bg-white p-16 text-center rounded-xl border border-stone-200 shadow-xs">
          <RefreshCw className="w-8 h-8 animate-spin text-[#a9bd77] mx-auto mb-3" />
          <h3 className="text-sm font-bold text-stone-800">
            Synthesizing Statutory Court of Inquiry Draft...
          </h3>
          <p className="text-xs text-stone-400 mt-1 max-w-md mx-auto">
            Structuring the assembly page (In lieu of IAFD-931), witness Q&amp;A testimonies, factual findings with citations, and legal opinions.
          </p>
        </div>
      ) : hasDraftContent ? (
        <div className="space-y-6">
          {/* ========================================================
              DOCUMENT PAGE 1: TITLE & ASSEMBLY (In lieu of IAFD - 931)
              ======================================================== */}
          <div className="draft-page p-8 md:p-12 rounded-xl border border-stone-300 shadow-sm font-serif text-stone-900 space-y-6">
            {/* Header Right */}
            <div className="text-right">
              <span className="font-bold underline text-sm tracking-wide">
                In lieu of IAFD – 931
              </span>
            </div>

            {/* Assembly Details Table */}
            <div className="space-y-2 text-sm leading-relaxed max-w-2xl">
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 font-bold">Proceed of</span>
                <span className="col-span-8">: {header.proceed_of || 'Court of Inquiry'}</span>
              </div>
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 font-bold">Assembled at</span>
                <span className="col-span-8">: {header.assembled_at || 'Station HQ, RTR Marg, New Delhi-10'}</span>
              </div>
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 font-bold">On time</span>
                <span className="col-span-8">: {header.on_time || '27 Jul 2026 and subsequent days.'}</span>
              </div>
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 font-bold">By order of</span>
                <span className="col-span-8">: {header.by_order_of || 'Convening Authority Part I Order'}</span>
              </div>
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 font-bold">For the purpose of</span>
                <span className="col-span-8">: {header.for_the_purpose_of}</span>
              </div>
            </div>

            {/* Court Composition Block */}
            <div className="pt-4 border-t border-stone-200 space-y-2 text-sm">
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 font-bold">Presiding Officer</span>
                <span className="col-span-8">: {comp[0]?.rank_name || 'JC-XXXXX Rank XXXXXX'}</span>
              </div>
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4 font-bold">Members</span>
                <span className="col-span-8">1. {comp[1]?.rank_name || 'JC-XXXXX Rank XXXXXX'}</span>
              </div>
              <div className="grid grid-cols-12 gap-2">
                <span className="col-span-4"></span>
                <span className="col-span-8">2. {comp[2]?.rank_name || 'No-XXXXXX Rank XXXXXXX'}</span>
              </div>
            </div>

            {/* Assembly Declaration */}
            <div className="pt-6 border-t border-stone-200 text-sm leading-relaxed text-justify">
              <p>
                {header.assembly_declaration || (
                  `The court of inquiry having assembled pursuant to order proceeded to investigate the circumstances under which ${header.for_the_purpose_of}.`
                )}
              </p>
            </div>
          </div>

          {/* ========================================================
              DOCUMENT PAGES 2+: WITNESS PROCEEDINGS (Q&A FORMAT)
              ======================================================== */}
          {witnesses.map((wit, wIdx) => (
            <div 
              key={wIdx} 
              className="draft-page p-8 md:p-12 rounded-xl border border-stone-300 shadow-sm font-serif text-stone-900 space-y-5"
            >
              <div className="text-center pb-2 border-b border-stone-200">
                <h3 className="text-base font-bold tracking-wide">
                  {wit.title || `Witness No ${wIdx + 1}`}
                </h3>
              </div>

              {/* Warning Declaration */}
              <p className="text-sm leading-relaxed text-justify">
                {wit.warning_declaration}
              </p>

              {/* Posting & Duties */}
              <p className="text-sm leading-relaxed text-justify">
                {wit.posting_and_duties}
              </p>

              {/* Narrative Statement */}
              <p className="text-sm leading-relaxed text-justify">
                {wit.narrative_statement}
              </p>

              {/* Question by the Court Heading */}
              <div className="pt-3">
                <h4 className="text-sm font-bold tracking-wide mb-3">
                  Question by the Court
                </h4>

                <div className="space-y-3">
                  {wit.questions_by_court?.map((qa, qIdx) => (
                    <div key={qIdx} className="text-sm leading-relaxed space-y-0.5">
                      <div className="font-bold text-stone-900">{qa.q}</div>
                      <div className="text-stone-800 pl-4">{qa.ans}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Closing Affirmation */}
              <p className="text-sm leading-relaxed pt-4 border-t border-stone-200 italic text-stone-700">
                {wit.closing_affirmation || "The above statement has been read to me in the language I understand and I sign it as correct."}
              </p>

              {/* Signature Blocks */}
              <div className="pt-6 flex justify-between items-end text-xs font-sans">
                <div>
                  <div className="font-semibold text-stone-800">
                    {wit.presiding_officer_sign || `Presiding Officer: ${comp[0]?.rank_name || 'JC-xxxx Rank Name'}`}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-stone-800">
                    {wit.witness_sign || '(Signature of Witness)'}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* ========================================================
              DOCUMENT PAGE 5: FINDING OF THE COURT
              ======================================================== */}
          <div className="draft-page p-8 md:p-12 rounded-xl border border-stone-300 shadow-sm font-serif text-stone-900 space-y-6">
            <div className="text-center pb-2 border-b border-stone-200">
              <h3 className="text-base font-bold tracking-wide">
                FINDING OF THE COURT
              </h3>
            </div>

            <div className="space-y-3.5 text-sm leading-relaxed">
              {findings.map((f, fIdx) => (
                <p key={fIdx} className="text-justify pl-2">
                  {f}
                </p>
              ))}
            </div>

            {/* Finding Signatures */}
            <div className="pt-8 border-t border-stone-200 space-y-3 text-sm font-sans max-w-md">
              <div className="flex items-center justify-between">
                <span className="font-bold">Presiding Officer :</span>
                <span className="border-b border-stone-400 pb-0.5 px-4 font-medium">({comp[0]?.rank_name || sigs.presiding_officer || 'JC-xxxx Rank Name'})</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold">Members 1. :</span>
                <span className="border-b border-stone-400 pb-0.5 px-4 font-medium">({comp[1]?.rank_name || sigs.members?.[0] || 'JC-xxxxxx Rank Name'})</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold pl-12">2. :</span>
                <span className="border-b border-stone-400 pb-0.5 px-4 font-medium">({comp[2]?.rank_name || sigs.members?.[1] || 'No-xxxxxx Rank Name'})</span>
              </div>
            </div>
          </div>

          {/* ========================================================
              DOCUMENT PAGE 6: OPINION OF THE COURT
              ======================================================== */}
          <div className="draft-page p-8 md:p-12 rounded-xl border border-stone-300 shadow-sm font-serif text-stone-900 space-y-6">
            <div className="text-center pb-2 border-b border-stone-200">
              <h3 className="text-base font-bold tracking-wide">
                OPINION OF THE COURT
              </h3>
            </div>

            <div className="space-y-3 text-sm leading-relaxed">
              {opinions.map((op, oIdx) => (
                <p key={oIdx} className="text-justify font-medium pl-2">
                  {op}
                </p>
              ))}
            </div>

            {/* Opinion Signatures */}
            <div className="pt-8 border-t border-stone-200 space-y-3 text-sm font-sans max-w-md">
              <div className="flex items-center justify-between">
                <span className="font-bold">Presiding Officer :</span>
                <span className="border-b border-stone-400 pb-0.5 px-4 font-medium">({comp[0]?.rank_name || sigs.presiding_officer || 'JC-xxxx Rank Name'})</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold">Members 1. :</span>
                <span className="border-b border-stone-400 pb-0.5 px-4 font-medium">({comp[1]?.rank_name || sigs.members?.[0] || 'JC-xxxxxx Rank Name'})</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold pl-12">2. :</span>
                <span className="border-b border-stone-400 pb-0.5 px-4 font-medium">({comp[2]?.rank_name || sigs.members?.[1] || 'No-xxxxxx Rank Name'})</span>
              </div>
            </div>
          </div>

          {/* ========================================================
              DOCUMENT PAGE 7: REMARKS OF OC TPS / CONVENING AUTHORITY
              ======================================================== */}
          <div className="draft-page p-8 md:p-12 rounded-xl border border-stone-300 shadow-sm font-serif text-stone-900 space-y-6">
            <div className="text-center pb-2 border-b border-stone-200">
              <h3 className="text-base font-bold tracking-wide">
                {remarks.title || 'REMARKS OF OC TPS, PMO CIDSS ON THE COURT OF INQUIRY'}
              </h3>
            </div>

            <div className="space-y-3 text-sm leading-relaxed">
              {remarks.points?.map((pt, pIdx) => (
                <p key={pIdx} className="text-justify pl-2 font-medium">
                  {pt}
                </p>
              ))}
            </div>

            {/* Station and Date Block */}
            <div className="pt-8 border-t border-stone-200 text-sm font-sans space-y-1">
              <div>{remarks.station || 'Station: Delhi Cantt-10'}</div>
              <div>{remarks.date || 'Date : August 2026.'}</div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="bg-white p-5 rounded-xl border border-[#3c4526] flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xs print:hidden">
            <button
              onClick={onPrevStep}
              className="px-4 py-2 text-xs font-medium text-[#b2bc94] hover:text-[#edf0d9] bg-[#272e17] hover:bg-[#2c3319] border border-[#3c4526] rounded-lg transition cursor-pointer"
            >
              &larr; Back to Officer Review
            </button>

            <div className="flex items-center gap-3">
              <button
                onClick={handlePrint}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#272e17] hover:bg-[#2c3319] text-[#d7debc] border border-[#3c4526] rounded-lg text-xs font-medium transition cursor-pointer"
              >
                <Printer className="w-4 h-4" />
                <span>Print Report</span>
              </button>

              <button
                onClick={handleDownloadDocx}
                className="flex items-center gap-1.5 px-5 py-2.5 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
              >
                <Download className="w-4 h-4" />
                <span>Download Official DOCX (IAFD-931)</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white p-16 text-center rounded-xl border border-dashed border-[#3c4526]">
          <FileText className="w-10 h-10 text-[#8b9771] mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-[#edf0d9]">No Draft Available</h3>
          <p className="text-xs text-[#98a477] mt-1 max-w-sm mx-auto">
            Please ensure Convening Order is uploaded and click below to synthesize proceedings.
          </p>
          <button
            onClick={handleGenerateDraft}
            className="mt-4 px-4 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
          >
            Generate Proceedings Draft
          </button>
        </div>
      )}
    </div>
  );
}
