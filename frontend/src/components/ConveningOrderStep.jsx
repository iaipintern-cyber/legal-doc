import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, ArrowRight, RefreshCw, Eye } from 'lucide-react';

export default function ConveningOrderStep({ caseState, onUpdateCase, onNextStep }) {
  const [uploading, setUploading] = useState(false);
  const [showRawText, setShowRawText] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const conveningOrder = caseState?.convening_order || {};
  const parsed = conveningOrder?.parsed;

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setErrorMsg('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload/convening-order', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
      } else {
        setErrorMsg('Failed to process convening order');
      }
    } catch (err) {
      setErrorMsg(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-5 font-sans">
      {/* Top Header Card */}
      <div className="bg-white p-5 rounded-xl border border-[#3c4526] shadow-xs flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#edf0d9]">1. Convening Order (PDF)</h2>
            <span className="text-[10px] font-medium uppercase tracking-wider bg-[#5d7430]/15 text-[#a9bd77] px-2 py-0.5 rounded border border-[#7d9440]/30">
              Scanned / Digital Supported
            </span>
          </div>
          <p className="text-xs text-[#b2bc94] mt-0.5">
            Upload the convening order (hard copy scanned or online soft copy) to initiate automated OCR extraction and military legal analysis.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg font-medium">
          {errorMsg}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Upload Box */}
        <div className="bg-white p-5 rounded-xl border border-[#3c4526] flex flex-col justify-between shadow-xs">
          <div>
            <h3 className="text-xs font-semibold text-[#c2cb9f] uppercase tracking-wider mb-3">
              Upload Convening Order (PDF)
            </h3>

            <div className="border-2 border-dashed border-[#4f5936] hover:border-[#7d9440] rounded-lg p-6 text-center bg-[#272e17] hover:bg-[#2c3319] transition cursor-pointer">
              <input
                type="file"
                id="convening-file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileUpload}
                className="hidden"
                disabled={uploading}
              />
              <label htmlFor="convening-file" className="cursor-pointer flex flex-col items-center justify-center space-y-2">
                <div className="w-11 h-11 rounded-full bg-white border border-[#3c4526] flex items-center justify-center text-[#a9bd77] shadow-xs">
                  {uploading ? (
                    <RefreshCw className="w-5 h-5 animate-spin text-[#a9bd77]" />
                  ) : (
                    <UploadCloud className="w-6 h-6 text-[#a9bd77]" />
                  )}
                </div>
                <span className="text-xs font-medium text-[#edf0d9]">
                  {uploading ? 'Analyzing with OCR & LLM...' : 'Upload Convening Order (PDF)'}
                </span>
                <span className="text-[11px] text-[#909c74]">Scanned hard copies &amp; digital PDFs</span>
              </label>
            </div>
          </div>

          {conveningOrder.file_name && (
            <div className="mt-4 pt-3 border-t border-[#2f3619] flex items-center justify-between text-xs">
              <span className="text-[#a9bd77] font-medium flex items-center gap-1.5 truncate max-w-[180px]">
                <CheckCircle2 className="w-4 h-4 text-[#a9bd77] shrink-0" />
                {conveningOrder.file_name}
              </span>
              <button
                onClick={() => setShowRawText(!showRawText)}
                className="text-[#b2bc94] hover:text-[#edf0d9] text-xs underline cursor-pointer"
              >
                {showRawText ? 'Hide Text' : 'View Text'}
              </button>
            </div>
          )}
        </div>

        {/* Summary Card */}
        <div className="md:col-span-2 bg-white p-5 rounded-xl border border-[#3c4526] shadow-xs">
          <h3 className="text-xs font-semibold text-[#c2cb9f] uppercase tracking-wider mb-3 pb-2 border-b border-[#2f3619]">
            Order Summary &amp; Military Details
          </h3>

          {parsed ? (
            <div className="space-y-4 text-xs">
              {/* Briefing Box */}
              <div className="p-3.5 bg-[#2c3319] border border-[#39421f] rounded-lg text-[#edf0d9] leading-relaxed">
                <strong className="text-[#eef1d9] block mb-1 font-semibold">Executive Briefing:</strong>
                {parsed.executive_summary || conveningOrder.summary || 'Convening order analyzed.'}
              </div>

              {/* 2-column info */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                  <span className="text-[#98a477] text-[11px] block font-normal">Convening Authority</span>
                  <span className="font-semibold text-[#edf0d9]">{parsed.convening_authority || 'Specified in Order'}</span>
                </div>

                <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                  <span className="text-[#98a477] text-[11px] block font-normal">Order Ref &amp; Date</span>
                  <span className="font-semibold text-[#edf0d9]">
                    {parsed.order_number || 'As per Order'} {parsed.date_of_order ? `• ${parsed.date_of_order}` : ''}
                  </span>
                </div>

                <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                  <span className="text-[#98a477] text-[11px] block font-normal">Subject / Incident</span>
                  <span className="font-semibold text-[#edf0d9]">
                    {parsed.subject_matter || parsed.incident_details?.nature_of_incident || 'Court of Inquiry Subject'}
                  </span>
                  {parsed.incident_details?.incident_date_time && (
                    <div className="text-[#98a477] text-[11px] mt-0.5">
                      Date/Time: {parsed.incident_details.incident_date_time}
                    </div>
                  )}
                </div>

                <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                  <span className="text-[#98a477] text-[11px] block font-normal">Terms of Reference</span>
                  <span className="text-[#d7debc] font-normal">
                    {parsed.terms_of_reference?.join(', ') || parsed.subject_matter || 'Terms of reference outlined in order.'}
                  </span>
                </div>
              </div>

              {/* Composition */}
              <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                <span className="text-[#98a477] text-[11px] block mb-1.5 font-semibold uppercase tracking-wider">Court Members Appointed:</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {parsed.composition_of_court && parsed.composition_of_court.length > 0 ? (
                    parsed.composition_of_court.map((m, i) => (
                      <div key={i} className="bg-white p-2.5 rounded border border-[#333b21] text-[#edf0d9] shadow-xs">
                        <div className="text-[10px] text-[#e0655a] font-medium uppercase">{m.role}</div>
                        <div className="font-semibold text-[#edf0d9]">{m.rank} {m.name || 'Officer'}</div>
                        <div className="text-[10px] text-[#98a477]">{m.service_no || m.unit || ''}</div>
                      </div>
                    ))
                  ) : (
                    <span className="text-[#98a477]">Extracted from order.</span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-[#98a477] text-xs">
              <FileText className="w-8 h-8 mx-auto mb-2 text-[#8b9771]" />
              <span>Awaiting Convening Order PDF. Upload a PDF on the left to extract text and begin the analysis.</span>
            </div>
          )}
        </div>
      </div>

      {/* Raw Text Drawer */}
      {showRawText && conveningOrder.raw_text && (
        <div className="bg-white p-4 rounded-xl border border-[#3c4526]">
          <div className="text-xs font-semibold text-[#c2cb9f] mb-2">Extracted Text (via Hybrid OCR Engine):</div>
          <pre className="bg-[#272e17] p-3 rounded-lg text-xs text-[#d7debc] whitespace-pre-wrap max-h-48 overflow-y-auto border border-[#333b21] font-mono">
            {conveningOrder.raw_text}
          </pre>
        </div>
      )}

      {/* Bottom Nav */}
      <div className="flex justify-end pt-2">
        <button
          onClick={onNextStep}
          disabled={!parsed && !conveningOrder.raw_text}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition cursor-pointer shadow-xs ${
            parsed || conveningOrder.raw_text
              ? 'bg-[#5d7430] hover:bg-[#4f6129] text-white'
              : 'bg-[#2b3318] text-[#7a8560] cursor-not-allowed'
          }`}
        >
          <span>Next: Supporting Documents &amp; Laws</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
