import React, { useState } from 'react';
import { UploadCloud, Scale, RefreshCw, ArrowRight, ArrowLeft, Trash2, FileText, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function EvidenceAndLawsStep({ caseState, onUpdateCase, onNextStep, onPrevStep }) {
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [analyzingCase, setAnalyzingCase] = useState(false);
  const [analysisElapsed, setAnalysisElapsed] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const supportingDocs = caseState?.supporting_docs || [];
  const analysis = caseState?.case_analysis;

  const MAX_FILE_SIZE = 3 * 1024 * 1024; // 3 MB
  const MAX_DOCS = 12;

  const handleUploadFiles = async (e) => {
    const files = Array.from(e.target.files);
    if (!files || files.length === 0) return;

    setErrorMsg('');

    // Check count limit
    if (supportingDocs.length + files.length > MAX_DOCS) {
      setErrorMsg(`Maximum ${MAX_DOCS} PDFs allowed. You currently have ${supportingDocs.length} uploaded.`);
      return;
    }

    // Check size limit for each file
    for (const f of files) {
      if (f.size > MAX_FILE_SIZE) {
        setErrorMsg(`"${f.name}" exceeds the 3 MB limit (${(f.size / (1024 * 1024)).toFixed(2)} MB). Please upload files under 3 MB.`);
        return;
      }
    }

    setUploadingDoc(true);
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    try {
      const res = await fetch('/api/upload/supporting-docs', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
      } else {
        setErrorMsg(data.detail || 'Failed to upload documents.');
      }
    } catch (err) {
      setErrorMsg(`Upload failed: ${err.message}`);
    } finally {
      setUploadingDoc(false);
      e.target.value = '';
    }
  };

  const handleDeleteDoc = async (docId) => {
    try {
      const res = await fetch(`/api/upload/supporting-docs/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
      }
    } catch (err) {
      console.error('Error deleting document:', err);
    }
  };

  const handleRunAnalysis = async () => {
    setAnalyzingCase(true);
    setErrorMsg('');
    const started = Date.now();
    const timer = setInterval(() => {
      setAnalysisElapsed(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    try {
      const res = await fetch('/api/analyze/case-brief', { method: 'POST' });
      const raw = await res.text();
      let data = {};
      try { data = JSON.parse(raw); } catch { /* empty or non-JSON body */ }
      if (!res.ok || !data.success || !data.job_id) {
        setErrorMsg(data.detail || 'Could not start the analysis. Please try again.');
        return;
      }

      // The LLM runs in the background; poll the job every 5 s so the
      // connection is never held open while the model is thinking.
      for (;;) {
        await new Promise((r) => setTimeout(r, 5000));
        let sData = {};
        try {
          const sRes = await fetch(`/api/analyze/status/${data.job_id}`);
          const sRaw = await sRes.text();
          try { sData = JSON.parse(sRaw); } catch { /* keep polling */ }
          if (sRes.status === 404) {
            setErrorMsg(sData.detail || 'Analysis job was lost (server restarted). Please run the analysis again.');
            return;
          }
        } catch { /* transient network hiccup -- keep polling */ }

        if (sData.status === 'done') {
          const caseRes = await fetch('/api/case/current');
          const caseData = await caseRes.json();
          onUpdateCase(caseData);
          return;
        }
        if (sData.status === 'error') {
          setErrorMsg(sData.detail || 'The analysis failed on the server. Please try again.');
          return;
        }
      }
    } catch (err) {
      setErrorMsg(`Analysis error: ${err.message}`);
    } finally {
      clearInterval(timer);
      setAnalysisElapsed(null);
      setAnalyzingCase(false);
    }
  };

  return (
    <div className="space-y-5 font-sans">
      {/* Top Header Card */}
      <div className="bg-white p-5 rounded-xl border border-[#3c4526] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
        <div>
          <h2 className="text-base font-semibold text-[#edf0d9]">2. Supporting Documents &amp; Case Brief</h2>
          <p className="text-xs text-[#b2bc94] mt-0.5">
            Upload case exhibits (technical, FIR, medical reports) and synthesize incident findings.
          </p>
        </div>

        <button
          onClick={handleRunAnalysis}
          disabled={analyzingCase || !caseState?.convening_order?.raw_text}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition cursor-pointer shadow-xs shrink-0 ${
            caseState?.convening_order?.raw_text
              ? 'bg-[#5d7430] hover:bg-[#4f6129] text-white'
              : 'bg-[#2b3318] text-[#7a8560] cursor-not-allowed'
          }`}
        >
          {analyzingCase ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Scale className="w-3.5 h-3.5" />}
          <span>Generate Incident &amp; Legal Analysis</span>
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2 font-medium">
          <AlertTriangle className="w-4 h-4 shrink-0 text-[#e0655a]" />
          <span>{errorMsg}</span>
        </div>
      )}

      {analyzingCase && (
        <div className="p-3 bg-[#2b3318] border border-[#414b28] text-[#d7debc] text-xs rounded-lg flex items-center gap-2 font-medium">
          <RefreshCw className="w-4 h-4 shrink-0 animate-spin text-[#8b9771]" />
          <span>
            Analysis is running in the background
            {analysisElapsed !== null ? ` -- ${analysisElapsed}s elapsed` : ''}. The offline model can take several
            minutes on large case files; please keep this tab open.
          </span>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Col (5 cols): Upload Supporting Documents */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white p-5 rounded-xl border border-[#3c4526] shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-[#c2cb9f] uppercase tracking-wider">
                Upload Supporting Documents
              </h3>
              <span className="text-xs text-[#e0655a] font-medium font-mono">
                {supportingDocs.length} / {MAX_DOCS}
              </span>
            </div>

            {/* Instruction description */}
            <p className="text-xs text-[#b2bc94] mb-4">
              Up to 12 PDFs, maximum 3 MB each.
            </p>

            {/* Single Upload Button */}
            <div className="mb-4">
              <label className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#272e17] hover:bg-[#2c3319] text-[#a9bd77] border-2 border-dashed border-[#4f5936] hover:border-[#7d9440] rounded-xl cursor-pointer transition text-xs font-medium">
                <input
                  type="file"
                  accept=".pdf"
                  multiple
                  onChange={handleUploadFiles}
                  className="hidden"
                  disabled={uploadingDoc || supportingDocs.length >= MAX_DOCS}
                />
                {uploadingDoc ? (
                  <RefreshCw className="w-4 h-4 animate-spin text-[#a9bd77]" />
                ) : (
                  <UploadCloud className="w-4 h-4 text-[#a9bd77]" />
                )}
                <span>
                  {uploadingDoc ? 'Uploading & Extracting...' : 'Upload Supporting Documents (PDF)'}
                </span>
              </label>
            </div>

            {/* Uploaded Documents List */}
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {supportingDocs.length > 0 ? (
                supportingDocs.map((doc, idx) => (
                  <div
                    key={doc.id || idx}
                    className="p-2.5 bg-[#272e17] border border-[#333b21] rounded-lg flex items-center justify-between text-xs group"
                  >
                    <div className="truncate max-w-[240px] flex items-center gap-2">
                      <FileText className="w-4 h-4 text-[#a9bd77] shrink-0" />
                      <div className="truncate">
                        <span className="font-medium text-[#edf0d9] block truncate">{doc.file_name}</span>
                        <span className="text-[10px] text-[#98a477] block font-mono">
                          Exhibit {String.fromCharCode(66 + idx)} {doc.size_kb ? `• ${doc.size_kb} KB` : ''}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteDoc(doc.id)}
                      className="p-1 text-[#98a477] hover:text-[#e0655a] rounded transition cursor-pointer"
                      title="Remove exhibit"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              ) : (
                <div className="p-6 bg-[#272e17] text-center text-xs text-[#98a477] rounded-lg border border-dashed border-[#333b21]">
                  No supporting documents uploaded yet. Witness questions will be generated from the Convening Order and any documents you add here.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Col (7 cols): AI Analysis Brief */}
        <div className="lg:col-span-7 bg-white p-5 rounded-xl border border-[#3c4526] shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-semibold text-[#c2cb9f] uppercase tracking-wider mb-3 pb-2 border-b border-[#2f3619]">
              Case Brief &amp; Incident Findings
            </h3>

            {analysis ? (
              <div className="space-y-3.5 text-xs">
                {/* 1. Timeline */}
                <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                  <strong className="text-[#edf0d9] block mb-1 text-[11px] uppercase font-semibold">
                    1. When &amp; Where Incident Occurred
                  </strong>
                  <div className="grid grid-cols-2 gap-2 text-[#d7debc]">
                    <div>
                      <span className="text-[#98a477] text-[11px] block">Date &amp; Time:</span>
                      <span className="font-semibold text-[#edf0d9]">{analysis.incident_overview?.date_and_time || 'Recorded in order'}</span>
                    </div>
                    <div>
                      <span className="text-[#98a477] text-[11px] block">Location / Circumstances:</span>
                      <span className="font-semibold text-[#edf0d9]">
                        {analysis.incident_overview?.location || 'Stated in proceedings'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Subject / Incident statement verbatim from the Convening Order */}
                {(analysis.incident_overview?.full_subject_statement || caseState?.convening_order?.parsed?.subject_matter) && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1 text-[11px] uppercase font-semibold">
                      Subject / Incident (exactly as in the Convening Order)
                    </strong>
                    <p className="text-[#d7debc] leading-relaxed">
                      {analysis.incident_overview?.full_subject_statement || caseState?.convening_order?.parsed?.subject_matter}
                    </p>
                  </div>
                )}

                {/* Sequence of events */}
                {analysis.incident_overview?.sequence_of_events?.length > 0 && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1.5 text-[11px] uppercase font-semibold">
                      Sequence of Events
                    </strong>
                    <ol className="space-y-1 text-[#d7debc] list-decimal pl-4">
                      {analysis.incident_overview.sequence_of_events.map((ev, i) => (
                        <li key={i} className="leading-relaxed">{ev}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* 2. Parties & Damages */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1 text-[11px] uppercase font-semibold">
                      2. Personnel Investigated / Involved
                    </strong>
                    <div className="text-[#d7debc] space-y-1">
                      {analysis.parties_involved?.individuals_investigated?.map((ind, i) => (
                        <div key={i} className="border-b border-[#2f3619] pb-1 last:border-b-0">
                          <div className="font-semibold text-[#edf0d9]">{ind.rank_and_name} ({ind.service_no || ind.unit || 'Service Pers'})</div>
                          <div className="text-[#98a477] text-[11px]">Role: {ind.role_in_incident}</div>
                          {ind.status_or_fitness && (
                            <div className="text-[10px] text-[#a9bd77] font-medium">{ind.status_or_fitness}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1 text-[11px] uppercase font-semibold">
                      3. Casualties &amp; Damage
                    </strong>
                    <div className="text-[#d7debc] space-y-1">
                      <div>
                        <span className="text-[#98a477] text-[11px] block">Injuries:</span>
                        <span className="font-medium text-[#e0655a]">
                          {analysis.parties_involved?.victim_and_damage_summary?.injured_personnel?.join(', ') || 'Recorded in medical report'}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#98a477] text-[11px] block">Damages:</span>
                        <span className="font-medium text-[#edf0d9]">
                          {analysis.parties_involved?.victim_and_damage_summary?.military_property_damaged?.join(', ') || 'Inspected property'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Root Cause Analysis */}
                <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                  <strong className="text-[#edf0d9] block mb-1 text-[11px] uppercase font-semibold">
                    4. Cause &amp; Attributability Assessment
                  </strong>
                  <p className="text-[#d7debc] mb-1 leading-relaxed">
                    <strong className="text-[#edf0d9]">Primary Cause:</strong> {analysis.root_cause_analysis?.primary_cause || 'Circumstances analyzed.'}
                  </p>
                  <p className="text-[#d7debc] leading-relaxed">
                    <strong className="text-[#edf0d9]">Blame Verdict:</strong> {analysis.root_cause_analysis?.culpability_verdict || 'Assessment pending on the available evidence.'}
                  </p>
                  {analysis.incident_overview?.conditions_weather_road_or_site && (
                    <p className="text-[#d7debc] leading-relaxed mt-1">
                      <strong className="text-[#edf0d9]">Conditions:</strong> {analysis.incident_overview.conditions_weather_road_or_site}
                    </p>
                  )}
                </div>

                {/* 5. Chronology of Events */}
                {analysis.chronology_of_events?.length > 0 && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1.5 text-[11px] uppercase font-semibold">
                      5. Chronology of Events
                    </strong>
                    <div className="space-y-1.5">
                      {analysis.chronology_of_events.map((row, i) => (
                        <div key={i} className="text-[#d7debc] border-b border-[#2f3619] pb-1 last:border-b-0">
                          <span className="text-[#a9bd77] font-semibold">{row.time || 'Time not stated'}</span>
                          <span className="mx-1 text-[#98a477]">|</span>
                          <span>{row.event}</span>
                          <span className="block text-[10px] text-[#98a477]">Source: {row.source_document || 'Not stated'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 6. Exhibits and what they establish */}
                {analysis.exhibits_and_their_findings?.length > 0 && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1.5 text-[11px] uppercase font-semibold">
                      6. Exhibits &amp; What They Establish
                    </strong>
                    <div className="space-y-1.5">
                      {analysis.exhibits_and_their_findings.map((ex, i) => (
                        <div key={i} className="text-[#d7debc] border-b border-[#2f3619] pb-1 last:border-b-0">
                          <span className="font-semibold text-[#edf0d9]">{ex.exhibit}</span>
                          <span className="text-[10px] text-[#98a477] ml-1">({ex.document_type || 'Document'})</span>
                          <div className="text-[11px]">{ex.what_it_establishes}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 7. Focus areas & evidence gaps */}
                {(analysis.areas_requiring_detailed_probing?.length > 0 || analysis.evidence_gaps?.length > 0) && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1.5 text-[11px] uppercase font-semibold">
                      7. Focus Areas &amp; Gaps in the Record
                    </strong>
                    {analysis.areas_requiring_detailed_probing?.length > 0 && (
                      <ul className="space-y-1 text-[#d7debc] list-disc pl-4">
                        {analysis.areas_requiring_detailed_probing.map((a, i) => (
                          <li key={`p${i}`} className="leading-relaxed">{a}</li>
                        ))}
                      </ul>
                    )}
                    {analysis.evidence_gaps?.length > 0 && (
                      <ul className="space-y-1 text-[#e0b25a] list-disc pl-4 mt-1.5">
                        {analysis.evidence_gaps.map((g, i) => (
                          <li key={`g${i}`} className="leading-relaxed">{g}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {/* 8. Loss and damage breakdown */}
                {analysis.financial_loss_breakdown?.length > 0 && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1.5 text-[11px] uppercase font-semibold">
                      8. Loss &amp; Damage Breakdown
                    </strong>
                    <div className="space-y-1 text-[#d7debc]">
                      {analysis.financial_loss_breakdown.map((f, i) => (
                        <div key={i} className="flex items-start justify-between gap-2 border-b border-[#2f3619] pb-1 last:border-b-0">
                          <span>{f.item}</span>
                          <span className="text-[#a9bd77] font-semibold shrink-0">{f.estimated_amount || 'Not stated'}</span>
                          <span className="text-[10px] text-[#98a477] shrink-0">{f.source_document || ''}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 9. Procedural compliance */}
                {analysis.procedural_compliance?.length > 0 && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1.5 text-[11px] uppercase font-semibold">
                      9. Procedural Compliance
                    </strong>
                    <div className="space-y-1.5">
                      {analysis.procedural_compliance.map((pc, i) => (
                        <div key={i} className="text-[#d7debc] border-b border-[#2f3619] pb-1 last:border-b-0">
                          <span className="font-semibold text-[#edf0d9]">{pc.requirement}</span>
                          <span className={`ml-2 text-[10px] font-medium ${String(pc.status || '').toLowerCase().includes('not') ? 'text-[#e0655a]' : 'text-[#a9bd77]'}`}>
                            {pc.status || 'Not stated in the documents'}
                          </span>
                          {pc.remarks && <div className="text-[11px]">{pc.remarks}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 4. Cross-correlation & Ambiguities */}
                {analysis.ambiguities_and_discrepancies && analysis.ambiguities_and_discrepancies.length > 0 && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <strong className="text-[#e0655a] block mb-1.5 flex items-center gap-1 font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Cross-Correlated Discrepancies &amp; Ambiguities:
                    </strong>
                    <div className="space-y-1.5">
                      {analysis.ambiguities_and_discrepancies.map((amb, i) => (
                        <div key={i} className="text-[11px] text-red-900 border-b border-red-200/60 pb-1 last:border-b-0">
                          <strong>{amb.subject}:</strong> {amb.finding}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 10. Court's Preliminary Opinion */}
                {analysis.court_preliminary_opinion && (
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <strong className="text-[#edf0d9] block mb-1 text-[11px] uppercase font-semibold">
                      10. Court&apos;s Preliminary Opinion
                    </strong>
                    <p className="text-[#d7debc] leading-relaxed">
                      {analysis.court_preliminary_opinion}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-16 text-[#98a477] text-xs">
                <span>Upload supporting documents and click "Generate Incident &amp; Legal Analysis" to correlate evidence.</span>
              </div>
            )}
          </div>

          {/* Bottom Nav */}
          <div className="flex justify-between items-center pt-4 mt-4 border-t border-[#2f3619]">
            <button
              onClick={onPrevStep}
              className="px-4 py-2 text-xs font-medium text-[#b2bc94] hover:text-[#edf0d9] bg-[#272e17] hover:bg-[#2c3319] border border-[#3c4526] rounded-lg transition cursor-pointer"
            >
              &larr; Back to Order
            </button>

            <button
              onClick={onNextStep}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
            >
              <span>Next: Witness Examination</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
