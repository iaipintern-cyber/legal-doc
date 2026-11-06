import React, { useState, useEffect } from 'react';
import { 
  Users, 
  UserPlus, 
  Save, 
  CheckCircle2, 
  ArrowRight, 
  ArrowLeft, 
  RefreshCw, 
  HelpCircle, 
  Sparkles, 
  FileText, 
  MessageSquareCheck,
  Edit3
} from 'lucide-react';

export default function WitnessStep({ caseState, onUpdateCase, onNextStep, onPrevStep }) {
  const witnesses = caseState?.witnesses || [];
  const [selectedWitnessId, setSelectedWitnessId] = useState(witnesses[0]?.id || null);
  const [generatingQ, setGeneratingQ] = useState(false);
  const [compilingStmt, setCompilingStmt] = useState(false);
  const [savingStmt, setSavingStmt] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [viewMode, setViewMode] = useState('qa'); // 'qa' | 'statement'

  const [activeWitness, setActiveWitness] = useState(null);
  const [qaAnswers, setQaAnswers] = useState([]);
  const [narrativeStatement, setNarrativeStatement] = useState('');

  const [newWitness, setNewWitness] = useState({
    name: '',
    rank: 'Naik',
    service_no: '',
    unit: '',
    ref_letter: String.fromCharCode(66 + witnesses.length)
  });

  // Keep active witness state synchronized
  useEffect(() => {
    const current = witnesses.find((w) => w.id === selectedWitnessId) || witnesses[0];
    setActiveWitness(current);
    if (current) {
      setNarrativeStatement(current.statement || '');
      // Initialize QA pairs
      if (current.qa_pairs && current.qa_pairs.length > 0) {
        setQaAnswers(current.qa_pairs);
      } else if (current.questions && current.questions.length > 0) {
        setQaAnswers(current.questions.map(q => ({ question: q, answer: '' })));
      } else {
        setQaAnswers([]);
      }
    }
  }, [selectedWitnessId, caseState?.witnesses]);

  const handleSelectWitness = (w) => {
    setSelectedWitnessId(w.id);
    setSaveSuccessMsg('');
  };

  const handleAnswerChange = (index, newAnswer) => {
    setQaAnswers(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], answer: newAnswer };
      return updated;
    });
  };

  // 1. Generate Probe Questions (strictly from this case's documents)
  const handleGenerateQuestions = async () => {
    if (!activeWitness) return;
    setGeneratingQ(true);
    setSaveSuccessMsg('');
    try {
      const res = await fetch('/api/witnesses/generate-questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ witness_id: activeWitness.id }),
      });
      const data = await res.json();
      if (data.success) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
        if (data.qa_pairs) {
          setQaAnswers(data.qa_pairs);
        }
        const qCount = Array.isArray(data.questions) ? data.questions.length : (data.qa_pairs?.length || 0);
        setSaveSuccessMsg(`${qCount} case-based questions generated for ${activeWitness.rank} ${activeWitness.name} (basic to advanced).`);
      }
    } catch (err) {
      console.error('Error generating questions:', err);
    } finally {
      setGeneratingQ(false);
    }
  };

  // 2. Save Q&A Pairs directly
  const handleSaveQA = async () => {
    if (!activeWitness) return;
    setSavingStmt(true);
    try {
      const res = await fetch('/api/witnesses/save-qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          witness_id: activeWitness.id,
          qa_pairs: qaAnswers
        })
      });
      if (res.ok) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
        setSaveSuccessMsg(`Answers for ${activeWitness.rank} ${activeWitness.name} saved.`);
      }
    } catch (err) {
      console.error('Error saving QA:', err);
    } finally {
      setSavingStmt(false);
    }
  };

  // 3. Synthesize all answers into official deposition using LLM
  const handleCompileWithLLM = async () => {
    if (!activeWitness) return;
    setCompilingStmt(true);
    setSaveSuccessMsg('');
    try {
      const res = await fetch('/api/witnesses/compile-statement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          witness_id: activeWitness.id,
          qa_pairs: qaAnswers,
          statement: narrativeStatement
        })
      });
      const data = await res.json();
      if (data.success) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
        if (data.witness?.statement) {
          setNarrativeStatement(data.witness.statement);
        }
        setViewMode('statement');
        setSaveSuccessMsg(`All answers compiled into statutory deposition for ${activeWitness.rank} ${activeWitness.name}!`);
      }
    } catch (err) {
      console.error('Error compiling statement:', err);
    } finally {
      setCompilingStmt(false);
    }
  };

  // 4. Save Final Statement
  const handleSaveStatement = async () => {
    if (!activeWitness) return;
    setSavingStmt(true);
    try {
      const res = await fetch('/api/witnesses/save-statement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          witness_id: activeWitness.id,
          statement: narrativeStatement,
        }),
      });
      if (res.ok) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
        setSaveSuccessMsg(`Statement finalized for ${activeWitness.rank} ${activeWitness.name}.`);
      }
    } catch (err) {
      console.error('Error saving statement:', err);
    } finally {
      setSavingStmt(false);
    }
  };

  const handleAddWitness = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/witnesses/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newWitness),
      });
      if (res.ok) {
        const caseRes = await fetch('/api/case/current');
        const caseData = await caseRes.json();
        onUpdateCase(caseData);
        setShowAddModal(false);
        const lastWitness = caseData.witnesses[caseData.witnesses.length - 1];
        if (lastWitness) {
          setSelectedWitnessId(lastWitness.id);
        }
        setNewWitness({
          name: '',
          rank: 'Naik',
          service_no: '',
          unit: '',
          ref_letter: String.fromCharCode(67 + witnesses.length)
        });
      }
    } catch (err) {
      console.error('Error adding witness:', err);
    }
  };

  return (
    <div className="space-y-5 font-sans">
      {/* Top Header Card */}
      <div className="bg-white p-5 rounded-xl border border-[#3c4526] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-[#edf0d9]">3. Witness Examination &amp; Statements</h2>
            <span className="text-[10px] font-medium uppercase tracking-wider bg-[#5d7430]/15 text-[#a9bd77] px-2 py-0.5 rounded border border-[#7d9440]/30">
              Witness Deposition
            </span>
          </div>
          <p className="text-xs text-[#b2bc94] mt-0.5">
            Generate case-specific questions ordered from basic to advanced, drawn strictly from the Convening Order and exhibits. Enter answers below each question and synthesize into the formal Court of Inquiry draft.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-[#b2bc94]">
            Witnesses: <strong className="text-[#edf0d9] font-medium">{witnesses.length}</strong>
          </span>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Add Witness</span>
          </button>
        </div>
      </div>

      {saveSuccessMsg && (
        <div className="p-3 bg-[#2c3319] border border-[#39421f] text-[#c8d0aa] text-xs rounded-lg flex items-center gap-2 font-normal">
          <CheckCircle2 className="w-4 h-4 text-[#a9bd77] shrink-0" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* Left Col (4 cols): Witness List */}
        <div className="md:col-span-4 bg-white p-4 rounded-xl border border-[#3c4526] shadow-xs">
          <h3 className="text-xs font-semibold text-[#c2cb9f] uppercase tracking-wider mb-3 pb-2 border-b border-[#2f3619] flex items-center justify-between">
            <span>Witness Roster</span>
            <span className="text-[10px] text-[#98a477] font-normal">IAFD-931 Order</span>
          </h3>

          {witnesses.length > 0 ? (
            <div className="space-y-2">
              {witnesses.map((w, index) => {
                const isSelected = w.id === (activeWitness?.id);
                const hasStatement = !!w.statement && w.statement.length > 10;
                const hasAnswers = w.qa_pairs && w.qa_pairs.some(q => q.answer && q.answer.trim().length > 0);

                return (
                  <button
                    key={w.id || index}
                    onClick={() => handleSelectWitness(w)}
                    className={`w-full text-left p-3 rounded-lg border transition cursor-pointer ${
                      isSelected
                        ? 'bg-[#2c3319] border-[#7d9440] shadow-xs'
                        : 'bg-[#272e17] hover:bg-[#313a1e] border-[#333b21] text-[#d7debc]'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="text-[#98a477]">
                        Witness No {index + 1} &bull; Ref {w.ref_letter || String.fromCharCode(66 + index)}
                      </span>
                      {hasStatement ? (
                        <span className="text-[#a9bd77] font-medium flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-[#a9bd77]" /> Recorded
                        </span>
                      ) : hasAnswers ? (
                        <span className="text-[#e0655a] font-normal">
                          Q&amp;A In Progress
                        </span>
                      ) : (
                        <span className="text-amber-700 font-normal">
                          Pending
                        </span>
                      )}
                    </div>
                    <div className="font-semibold text-[#edf0d9] text-xs">
                      {w.rank} {w.name}
                    </div>
                    <div className="text-[11px] text-[#98a477] truncate">
                      {w.unit ? `(${w.unit})` : ''}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-[#98a477] bg-[#272e17] rounded-lg border border-dashed border-[#333b21]">
              <Users className="w-6 h-6 mx-auto mb-1.5 text-[#8b9771]" />
              <span>No witnesses added yet. Click "+ Add Witness" to register the injured personnel or eyewitnesses.</span>
            </div>
          )}
        </div>

        {/* Right Col (8 cols): Active Witness Examination */}
        <div className="md:col-span-8 bg-white p-5 rounded-xl border border-[#3c4526] shadow-xs flex flex-col justify-between min-h-[480px]">
          {activeWitness ? (
            <div className="space-y-4">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#2f3619] gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-[#edf0d9]">
                      {activeWitness.rank} {activeWitness.name}
                    </h3>
                    <span className="text-[10px] font-mono bg-[#2b3218] text-[#c8d0aa] px-2 py-0.5 rounded border border-[#3c4526]">
                      {activeWitness.service_no || 'Army No.'}
                    </span>
                  </div>
                  <div className="text-xs text-[#b2bc94] mt-0.5">
                    Unit: <strong className="text-[#edf0d9] font-medium">{activeWitness.unit || 'PMO CIDSS'}</strong>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleGenerateQuestions}
                    disabled={generatingQ}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#2c3319] hover:bg-[#2a3118] text-[#a9bd77] border border-[#4f5936] rounded-lg text-xs font-medium transition cursor-pointer"
                    title="Generate case-based questions (basic to advanced) from the Convening Order & exhibits"
                  >
                    {generatingQ ? <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#a9bd77]" /> : <HelpCircle className="w-3.5 h-3.5 text-[#a9bd77]" />}
                    <span>Generate Questions</span>
                  </button>
                </div>
              </div>

              {/* View Mode Toggle: Interactive Q&A vs Compiled Statement */}
              <div className="flex items-center justify-between border-b border-[#2f3619] pb-2">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setViewMode('qa')}
                    className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition cursor-pointer ${
                      viewMode === 'qa'
                        ? 'bg-[#5d7430] text-white shadow-xs'
                        : 'text-[#b2bc94] hover:bg-[#272e17]'
                    }`}
                  >
                    <MessageSquareCheck className="w-3.5 h-3.5" />
                    <span>Interactive Q&amp;A Examination</span>
                  </button>

                  <button
                    onClick={() => setViewMode('statement')}
                    className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition cursor-pointer ${
                      viewMode === 'statement'
                        ? 'bg-[#5d7430] text-white shadow-xs'
                        : 'text-[#b2bc94] hover:bg-[#272e17]'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Synthesized Deposition (IAFD-931)</span>
                  </button>
                </div>

                {viewMode === 'qa' && (
                  <button
                    onClick={handleCompileWithLLM}
                    disabled={compilingStmt || qaAnswers.length === 0}
                    className="flex items-center gap-1.5 px-3 py-1 bg-[#b33324] hover:bg-[#bd3527] text-white rounded-md text-xs font-medium transition cursor-pointer shadow-xs disabled:opacity-50"
                    title="Synthesizes all individual answers into the formal Court of Inquiry draft format"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${compilingStmt ? 'animate-spin' : ''}`} />
                    <span>{compilingStmt ? 'Synthesizing Deposition...' : 'Synthesize With LLM'}</span>
                  </button>
                )}
              </div>

              {/* MODE 1: INTERACTIVE Q&A EXAMINATION */}
              {viewMode === 'qa' && (
                <div className="space-y-4">
                  {/* Narrative Background Input */}
                  <div className="bg-[#272e17] p-3 rounded-lg border border-[#333b21]">
                    <label className="block text-xs font-medium text-[#d7debc] mb-1">
                      Preliminary Statement / Duty Context (Paragraph 2 &amp; 3):
                    </label>
                    <textarea
                      rows={3}
                      value={narrativeStatement}
                      onChange={(e) => setNarrativeStatement(e.target.value)}
                      placeholder="e.g. On 23 May 2026 at 0730 Hrs, I was proceeding for duty from residence at APS Colony on bicycle when I lost control due to slippery road..."
                      className="w-full bg-white border border-[#414b28] rounded-md p-2.5 text-xs text-[#edf0d9] placeholder-[#717c58] focus:border-[#7d9440] focus:ring-1 focus:ring-[#7d9440] focus:outline-none transition"
                    />
                  </div>

                  {/* Sequential Questions with Direct Manual Answer Fields */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-[#edf0d9] uppercase tracking-wider">
                        Question by the Court (Enter Witness Answers Below):
                      </span>
                      <span className="text-[11px] text-[#98a477] italic">
                        {qaAnswers.length} questions &middot; ordered basic to advanced, based on this case
                      </span>
                    </div>

                    {qaAnswers.length > 0 ? (
                      <div className="space-y-3">
                        {qaAnswers.map((item, idx) => (
                          <div 
                            key={idx} 
                            className="bg-white p-3 rounded-lg border border-[#333b21] shadow-xs hover:border-[#7d9440] transition"
                          >
                            <div className="flex items-start gap-2 mb-1.5">
                              <span className="text-xs font-semibold text-[#e0655a] shrink-0 font-mono">
                                Q{idx + 1}.
                              </span>
                              <span className="text-xs font-medium text-[#edf0d9]">
                                {item.question.replace(/^Q\d+\.\s*/i, '')}
                              </span>
                            </div>

                            <div className="flex items-start gap-2">
                              <span className="text-xs font-medium text-[#a9bd77] shrink-0 pt-1.5 font-mono">
                                Ans.
                              </span>
                              <textarea
                                rows={2}
                                value={item.answer || ''}
                                onChange={(e) => handleAnswerChange(idx, e.target.value)}
                                placeholder={`Write answer given by ${activeWitness.rank} ${activeWitness.name} manually...`}
                                className="w-full bg-[#272e17] border border-[#414b28] rounded-md p-2 text-xs text-[#edf0d9] placeholder-[#717c58] focus:bg-white focus:border-[#7d9440] focus:ring-1 focus:ring-[#7d9440] focus:outline-none transition leading-relaxed"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 bg-[#272e17] rounded-lg border border-dashed border-[#333b21] p-6">
                        <HelpCircle className="w-8 h-8 text-[#a9bd77] mx-auto mb-2 opacity-60" />
                        <h4 className="text-xs font-semibold text-[#edf0d9]">No Questions Formulated Yet</h4>
                        <p className="text-xs text-[#98a477] mt-1 max-w-sm mx-auto">
                          Click "Generate Questions" to produce 20+ case-specific questions drawn only from the Convening Order and uploaded exhibits, ordered from basic to advanced.
                        </p>
                      </div>
                    )}

                    {qaAnswers.length > 0 && (
                      <div className="flex items-center justify-between pt-3">
                        <button
                          onClick={handleSaveQA}
                          disabled={savingStmt}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#272e17] hover:bg-[#2c3319] text-[#d7debc] border border-[#3c4526] rounded-md text-xs font-medium transition cursor-pointer"
                        >
                          <Save className="w-3.5 h-3.5" />
                          <span>{savingStmt ? 'Saving...' : 'Save Q&A Draft'}</span>
                        </button>

                        <button
                          onClick={handleCompileWithLLM}
                          disabled={compilingStmt}
                          className="flex items-center gap-1.5 px-4 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
                        >
                          <Sparkles className={`w-3.5 h-3.5 ${compilingStmt ? 'animate-spin' : ''}`} />
                          <span>{compilingStmt ? 'Synthesizing with LLM...' : 'Combine All Answers & Compile Deposition'}</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* MODE 2: SYNTHESIZED STATUTORY DEPOSITION (IAFD-931) */}
              {viewMode === 'statement' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[#edf0d9] uppercase tracking-wider">
                      Formal Witness Deposition (In lieu of IAFD - 931):
                    </span>
                    <button
                      onClick={() => setViewMode('qa')}
                      className="text-xs text-[#a9bd77] hover:underline flex items-center gap-1 font-medium"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>Edit Individual Q&amp;A</span>
                    </button>
                  </div>

                  <div className="bg-[#272e17] border border-[#333b21] rounded-xl p-4 font-mono text-xs leading-relaxed text-[#edf0d9] space-y-3 whitespace-pre-wrap max-h-[380px] overflow-y-auto">
                    {narrativeStatement || "No testimony synthesized yet. Return to Interactive Q&A to answer the questions and click 'Combine All Answers & Compile Deposition'."}
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={handleSaveStatement}
                      disabled={savingStmt}
                      className="flex items-center gap-1.5 px-4 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>{savingStmt ? 'Saving...' : 'Save & Confirm Deposition'}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-20 text-[#98a477] text-xs my-auto">
              <span>Select or add a witness on the left to begin examination.</span>
            </div>
          )}

          {/* Bottom Nav */}
          <div className="flex justify-between items-center pt-4 mt-4 border-t border-[#2f3619]">
            <button
              onClick={onPrevStep}
              className="px-4 py-2 text-xs font-medium text-[#b2bc94] hover:text-[#edf0d9] bg-[#272e17] hover:bg-[#2c3319] border border-[#3c4526] rounded-lg transition cursor-pointer"
            >
              &larr; Back to Exhibits
            </button>

            <button
              onClick={onNextStep}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#5d7430] hover:bg-[#4f6129] text-white rounded-lg text-xs font-medium transition cursor-pointer shadow-xs"
            >
              <span>Next: Presiding Officer Review</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Add Witness Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-5 border border-[#414b28] shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#2f3619]">
              <h3 className="text-sm font-semibold text-[#edf0d9]">Add New Witness to Proceedings</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-[#98a477] hover:text-[#edf0d9] text-base font-semibold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleAddWitness} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-[#d7debc] mb-1">Witness Full Name</label>
                <input
                  type="text"
                  required
                  value={newWitness.name}
                  onChange={(e) => setNewWitness({ ...newWitness, name: e.target.value })}
                  placeholder="e.g. Ramesh Kumar"
                  className="w-full bg-[#272e17] border border-[#414b28] rounded-lg p-2 text-xs text-[#edf0d9] focus:bg-white focus:border-[#7d9440] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#d7debc] mb-1">Rank</label>
                  <input
                    type="text"
                    required
                    value={newWitness.rank}
                    onChange={(e) => setNewWitness({ ...newWitness, rank: e.target.value })}
                    placeholder="e.g. Naik, Subedar, Nk"
                    className="w-full bg-[#272e17] border border-[#414b28] rounded-lg p-2 text-xs text-[#edf0d9] focus:bg-white focus:border-[#7d9440] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#d7debc] mb-1">Army / Service No.</label>
                  <input
                    type="text"
                    required
                    value={newWitness.service_no}
                    onChange={(e) => setNewWitness({ ...newWitness, service_no: e.target.value })}
                    placeholder="e.g. 15482910L, JC-XXXXX"
                    className="w-full bg-[#272e17] border border-[#414b28] rounded-lg p-2 text-xs text-[#edf0d9] focus:bg-white focus:border-[#7d9440] focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#d7debc] mb-1">Unit / Organisation</label>
                  <input
                    type="text"
                    value={newWitness.unit}
                    onChange={(e) => setNewWitness({ ...newWitness, unit: e.target.value })}
                    placeholder="e.g. PMO CIDSS, DGIS"
                    className="w-full bg-[#272e17] border border-[#414b28] rounded-lg p-2 text-xs text-[#edf0d9] focus:bg-white focus:border-[#7d9440] focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-[#2f3619]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 text-xs text-[#b2bc94] hover:bg-[#272e17] rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-[#5d7430] hover:bg-[#4f6129] text-white text-xs font-medium rounded-lg shadow-xs"
                >
                  Add Witness
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
