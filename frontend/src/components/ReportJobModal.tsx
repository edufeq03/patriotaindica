'use client';

import React, { useState } from 'react';
import { X, AlertTriangle, ShieldAlert, CheckCircle2, Loader2 } from 'lucide-react';

interface ReportJobModalProps {
  jobId: string;
  jobTitle: string;
  businessName: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function ReportJobModal({
  jobId,
  jobTitle,
  businessName,
  isOpen,
  onClose,
}: ReportJobModalProps) {
  const [reason, setReason] = useState<'golpe' | 'discriminacao' | 'improprio' | 'outro'>('golpe');
  const [details, setDetails] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reason,
          details: details.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Não foi possível registrar a denúncia.');
      }

      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setDetails('');
        onClose();
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Erro ao enviar denúncia. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-2xl bg-[#0d151c] border border-red-500/30 p-6 shadow-2xl text-left space-y-5">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#182836] transition-colors"
          title="Fechar"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 border-b border-[#182836] pb-4">
          <div className="p-2.5 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Denunciar Vaga de Emprego</h3>
            <p className="text-xs text-slate-400 truncate max-w-[280px]">
              {jobTitle} • {businessName}
            </p>
          </div>
        </div>

        {success ? (
          <div className="py-6 text-center space-y-3">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto animate-bounce" />
            <h4 className="text-sm font-bold text-white">Denúncia Enviada com Sucesso</h4>
            <p className="text-xs text-slate-400">
              Nossa equipe de curadoria analisará o anúncio imediatamente para garantir a integridade da plataforma.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-xl bg-red-950/80 border border-red-500/50 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Motivo da Irregularidade</label>
              <select
                value={reason}
                onChange={(e) => setReason(e.target.value as any)}
                className="w-full px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-red-500 outline-none"
              >
                <option value="golpe">Cobrança de taxa / Golpe / Dinheiro adiantado</option>
                <option value="discriminacao">Discriminação (exigência de foto, idade, sexo, crença)</option>
                <option value="improprio">Conteúdo impróprio / ofensivo / ilegal</option>
                <option value="outro">Outro motivo</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Detalhes ou Observações (opcional)</label>
              <textarea
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                maxLength={200}
                rows={3}
                placeholder="Explique brevemente o problema encontrado..."
                className="w-full px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder-slate-500 focus:border-red-500 outline-none resize-none"
              />
              <div className="text-[10px] text-right text-slate-500">
                {details.length}/200 caracteres
              </div>
            </div>

            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] leading-relaxed">
              💡 <strong>Importante</strong>: No Patriota Indica nenhuma empresa pode cobrar qualquer valor de inscrição ou exigir dados sensíveis e fotos no anúncio.
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#182836]">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition-all shadow-md shadow-red-950/50 flex items-center gap-1.5 disabled:opacity-50"
              >
                {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {loading ? 'Enviando...' : 'Confirmar Denúncia'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
