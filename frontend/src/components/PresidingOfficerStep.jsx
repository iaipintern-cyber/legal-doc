import React, { useState, useEffect } from 'react';
import { CheckSquare, ShieldCheck, ArrowRight, ArrowLeft, RefreshCw, Shield } from 'lucide-react';

export default function PresidingOfficerStep({ caseState, onUpdateCase, onNextStep, onPrevStep, user }) {
  const reviewState = caseState?.presiding_officer_review || {};
  const caseAnalysis = caseState?.case_analysis;
  
  const [checklist, setChecklist] = useState(() => {
    // Merge stored state over the defaults so checklists saved under the
    // older key name still work (and every box has a defined value).
    const defaults = {
      convening_order_authenticated: true,
      exhibits_catalogued: true,
      procedural_safeguards_complied: true,
      witness_testimonies_recorded_under_oath: true,
      technical_inspection_attached: true,
      damage_assessment_verified: true,
    };
    const stored = { ...(reviewState.checklist || {}) };
    // Carry over the value saved under the older key name, then drop it so it
    // does not keep the "all checked" gate permanently unsatisfied.
    if (stored.army_rule_180_complied !== undefined) {
      if (stored.procedural_safeguards_complied === undefined) {
        stored.procedural_safeguards_complied = stored.army_rule_180_complied;
      }
      delete stored.army_rule_180_complied;
    }
    return { ...defaults, ...stored };
  });

  const [comments, setComments] = useState(
    reviewState.comments ||
    caseAnalysis?.court_preliminary_opinion ||
    "The Court has reviewed the evidentiary record and witness depositions under oath. Procedural safeguards have been observed. The evidence gathered establishes the circumstances of the incident as documented."
  );

  useEffect(() => {
    if (!reviewState.comments && caseAnalysis?.court_preliminary_opinion) {
      setComments(caseAnalysis.court_preliminary_opinion);
    }
  }, [caseAnalysis]);

  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  const toggleCheck = (key) => {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const allChecked = Object.values(checklist).every(Boolean);

  const handleForwardToDraft = async () => {
    setSaving(true);
    setSuccessMsg('Verifying procedural compliance and pre-compiling Court of Inquiry draft (IAFD-931)...');
    try {
      // 1. Save Presiding Officer review
      const res = await fetch('/api/presiding-officer/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewed_by: "Admin",
          service_no: "",
          checklist: checklist,
          comments: comments,
          forwarded_to_draft: true,
        }),
      });

      // 2. Pre-generate the CoI draft so it's ready when Step 5 opens
      try {
        await fetch('/api/coi/generate', { method: 'POST' });
      } catch (genErr) {
        console.warn("Pre-generation trigger:", genErr);
      }

      const caseRes = await fetch('/api/case/current');
      const caseData = await caseRes.json();
      onUpdateCase(caseData);
      
      setSuccessMsg("Review approved. Forwarding to final draft...");
      setTimeout(() => {
        onNextStep();
      }, 400);
    } catch (err) {
      console.error("Error submitting review:", err);
      setSuccessMsg("Error forwarding review. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5 font-sans">
      {/* Top Header Card */}
      <div className="bg-white p-5 rounded-xl border border-[#3c4526] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#edf0d9]">4. Presiding Officer Review</h2>
            <span className="text-[10px] font-medium uppercase tracking-wider bg-[#5d7430]/15 text-[#a9bd77] px-2 py-0.5 rounded border border-[#7d9440]/30">
              Statutory Verification
            </span>
          </div>
          <p className="text-xs text-[#b2bc94] mt-0.5">
            Verify procedural compliance and forward the case to draft the final Court of Inquiry proceedings (In lieu of IAFD - 931).
          </p>
        </div>

        <div className="text-xs bg-[#272e17] px-3 py-1.5 rounded-lg border border-[#3c4526] text-[#d7debc] font-medium flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-[#e0655a]" />
          <span>Reviewer: <strong className="text-[#edf0d9]">Admin</strong></span>
        </div>
      </div>

      {successMsg && (
        <div className="p-3 bg-[#2c3319] border border-[#39421f] text-[#c8d0aa] text-xs rounded-lg flex items-center gap-2 font-normal">
          {saving ? <RefreshCw className="w-4 h-4 animate-spin shrink-0 text-[#a9bd77]" /> : <ShieldCheck className="w-4 h-4 text-[#a9bd77] shrink-0" />}
          <span>{successMsg}</span>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Checklist */}
        <div className="bg-white p-5 rounded-xl border border-[#3c4526] shadow-xs">
          <h3 className="text-xs font-semibold text-[#c2cb9f] uppercase tracking-wider mb-3 pb-2 border-b border-[#2f3619]">
            Procedural Verification Checklist
          </h3>

          <div className="space-y-2.5">
            {[
              {
                key: 'convening_order_authenticated',
                title: 'Convening Order Authenticated',
                desc: 'Authority signature, Part I order number, and mandate verified.'
              },
              {
                key: 'exhibits_catalogued',
                title: 'Exhibits Catalogued',
                desc: 'All documentary evidence and logs assembled as formal exhibits.'
              },
              {
                key: 'procedural_safeguards_complied',
                title: 'Procedural Safeguards Observed',
                desc: 'Full opportunity afforded to cross-examine and present defense.'
              },
              {
                key: 'witness_testimonies_recorded_under_oath',
                title: 'Witness Testimonies Recorded under Oath',
                desc: 'Formal warning issued and Question by the Court answered.'
              },
              {
                key: 'technical_inspection_attached',
                title: 'Medical & Technical Inspection Endorsed',
                desc: 'Hospital records and conveyance fitness verified.'
              },
              {
                key: 'damage_assessment_verified',
                title: 'Damage & Injury Attributability Assessed',
                desc: 'Attributability to military service on bonafide duty evaluated.'
              }
            ].map((item) => (
              <label
                key={item.key}
                onClick={() => toggleCheck(item.key)}
                className={`p-3 rounded-lg border flex items-start gap-3 cursor-pointer transition text-xs ${
                  checklist[item.key]
                    ? 'bg-[#2c3319] border-[#4f5936]'
                    : 'bg-[#272e17] border-[#333b21]'
                }`}
              >
                <input
                  type="checkbox"
                  checked={checklist[item.key]}
                  onChange={() => {}}
                  className="mt-0.5 rounded text-[#a9bd77] accent-[#93aa4e] cursor-pointer"
                />
                <div>
                  <div className={`font-medium ${checklist[item.key] ? 'text-[#edf0d9]' : 'text-[#b2bc94]'}`}>
                    {item.title}
                  </div>
                  <div className="text-[11px] text-[#98a477] mt-0.5">{item.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Opinion & Directive */}
        <div className="bg-white p-5 rounded-xl border border-[#3c4526] shadow-xs flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-[#c2cb9f] uppercase tracking-wider pb-2 border-b border-[#2f3619]">
              Officer Findings &amp; Directive
            </h3>

            <div>
              <label className="block text-xs font-medium text-[#d7debc] mb-1">
                Findings Endorsement Remarks:
              </label>
              <textarea
                rows={7}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                className="w-full bg-[#272e17] border border-[#414b28] rounded-lg p-3 text-xs text-[#edf0d9] placeholder-[#717c58] focus:bg-white focus:border-[#7d9440] focus:outline-none leading-relaxed transition"
              />
            </div>

            <div className="p-3 bg-[#272e17] border border-[#333b21] rounded-lg text-xs text-[#b2bc94]">
              <span className="font-semibold text-[#edf0d9] block">Reviewing Authority:</span>
              <span>Admin &bull; Presiding Officer Desk</span>
            </div>
          </div>

          {/* Action */}
          <div className="flex justify-between items-center pt-4 mt-4 border-t border-[#2f3619]">
            <button
              onClick={onPrevStep}
              className="px-4 py-2 text-xs font-medium text-[#b2bc94] hover:text-[#edf0d9] bg-[#272e17] hover:bg-[#2c3319] border border-[#3c4526] rounded-lg transition cursor-pointer"
            >
              &larr; Back to Witnesses
            </button>

            <button
              onClick={handleForwardToDraft}
              disabled={saving || !allChecked}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition cursor-pointer shadow-xs ${
                allChecked
                  ? 'bg-[#5d7430] hover:bg-[#4f6129] text-white'
                  : 'bg-[#2b3318] text-[#7a8560] cursor-not-allowed'
              }`}
            >
              <span>{saving ? 'Assembling Draft...' : 'Forward to Final Draft (IAFD-931)'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
