import React, { useState } from 'react';
import { ArrowRight, Lock, User } from 'lucide-react';

export default function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!username || !password) {
      setErrorMsg('Please enter username and password');
      return;
    }
    setLoading(true);
    setErrorMsg('');

    setTimeout(() => {
      onLogin({
        username: username,
        name: 'Admin',
        role: 'Admin'
      });
      setLoading(false);
    }, 300);
  };

  return (
    <div className="min-h-screen bg-[#171b0e] flex flex-col justify-center items-center px-4 font-sans">
      <div className="max-w-sm w-full bg-white p-8 rounded-2xl border border-[#3a4324] shadow-md">
        {/* Header with Army Emblem */}
        <div className="text-center mb-6">
          <div className="w-20 h-20 mx-auto mb-3 flex items-center justify-center">
            <img
              src="/army-logo.png"
              alt="Indian Army Emblem"
              className="w-full h-full object-contain drop-shadow-xs"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = '/image.png';
              }}
            />
          </div>
          <h2 className="text-lg font-semibold text-[#edf0d9] tracking-tight mb-1">
            Court of Inquiry Generation
          </h2>
          <div className="inline-block bg-[#b33324] text-white text-[10px] font-medium uppercase tracking-wider px-2.5 py-0.5 rounded shadow-xs mb-1">
            Military Legal Assistant Portal
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 p-2.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg text-center font-medium">
            {errorMsg}
          </div>
        )}

        {/* Minimal Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#c2cb9f] mb-1 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-[#a9bd77]" />
              <span>Username</span>
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              className="w-full bg-[#272e17] border border-[#414b28] rounded-lg px-3 py-2 text-sm text-[#edf0d9] placeholder-[#717c58] focus:bg-white focus:border-[#7d9440] focus:ring-1 focus:ring-[#7d9440] focus:outline-none transition"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#c2cb9f] mb-1 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-[#a9bd77]" />
              <span>Password</span>
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full bg-[#272e17] border border-[#414b28] rounded-lg px-3 py-2 text-sm text-[#edf0d9] placeholder-[#717c58] focus:bg-white focus:border-[#7d9440] focus:ring-1 focus:ring-[#7d9440] focus:outline-none transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#5d7430] hover:bg-[#4f6129] text-white font-medium py-2.5 px-4 rounded-lg transition flex items-center justify-center gap-2 text-sm shadow-xs cursor-pointer mt-2"
          >
            {loading ? (
              <span>Signing In...</span>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-[#2f3619] text-center">
          <p className="text-[11px] text-[#98a477]">
            Indian Armed Forces Official Inquiry System
          </p>
        </div>
      </div>
    </div>
  );
}
