'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Briefcase,
  Building2,
  MapPin,
  Clock,
  ShieldCheck,
  Send,
  AlertTriangle,
  Loader2,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import ReportJobModal from './ReportJobModal';

interface JobItem {
  id: string;
  title: string;
  description?: string | null;
  contract_type: string;
  openings_count: number;
  published_at?: string | null;
  expires_at?: string | null;
  business: {
    id: string;
    name: string;
    slug: string;
    city: string;
    neighborhood: string;
    logo_url?: string | null;
    category_name?: string | null;
  };
}

interface BusinessJobsModalProps {
  business: {
    id: string;
    name: string;
    city: string;
    neighborhood?: string;
    logo_url?: string | null;
    category_name?: string;
  } | null;
  isOpen: boolean;
  onClose: () => void;
}

const CONTRACT_TYPE_LABELS: Record<string, string> = {
  clt: 'CLT (Efetivo)',
  temporario: 'Temporário',
  meio_periodo: 'Meio Período',
  estagio: 'Estágio',
  aprendiz: 'Jovem Aprendiz',
  autonomo: 'Autônomo / PJ',
};

export default function BusinessJobsModal({
  business,
  isOpen,
  onClose,
}: BusinessJobsModalProps) {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Estado para denúncia
  const [reportJob, setReportJob] = useState<{ id: string; title: string } | null>(null);

  useEffect(() => {
    if (!isOpen || !business) {
      setTimeout(() => {
        setJobs([]);
        setError(null);
      }, 0);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetch(`/api/v1/jobs?business_id=${business.id}&limit=10`)
      .then((res) => {
        if (!res.ok) throw new Error('Falha ao carregar as vagas desta empresa.');
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setJobs(data.results || []);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Erro ao consultar vagas abertas.');
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, business]);

  if (!isOpen || !business) return null;

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
        <div className="relative w-full max-w-2xl max-h-[90vh] sm:max-h-[85vh] rounded-t-3xl sm:rounded-3xl bg-[#0d151c] border border-amber-500/30 p-5 sm:p-6 shadow-2xl flex flex-col space-y-4 overflow-hidden">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-[#182836] pb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-[#070b0e] border border-[#182836] flex items-center justify-center overflow-hidden shrink-0">
                {business.logo_url ? (
                  <img src={business.logo_url} alt={business.name} className="w-full h-full object-cover" />
                ) : (
                  <Building2 className="w-6 h-6 text-amber-400" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                    <Briefcase className="w-3 h-3 text-amber-400" />
                    Contratando
                  </span>
                  <span className="text-xs text-slate-400">
                    {business.city}
                  </span>
                </div>
                <h2 className="text-lg font-black text-white leading-tight mt-0.5">{business.name}</h2>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#182836] transition-colors"
              title="Fechar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Aviso de Proteção e Confiança */}
          <div className="p-3 rounded-xl bg-gradient-to-r from-emerald-950/40 to-[#070b0e] border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
            <span className="text-[11px] leading-relaxed">
              O Patriota Indica conecta candidatos diretamente ao WhatsApp da empresa <strong>sem intermediários</strong> e <strong>sem cobrança de taxas</strong>. Nunca pague por processos seletivos.
            </span>
          </div>

          {/* Lista de Vagas */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
            {loading && (
              <div className="py-12 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
                <span className="text-xs">Buscando vagas ativas...</span>
              </div>
            )}

            {error && (
              <div className="p-4 rounded-xl bg-red-950/50 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                <span>{error}</span>
              </div>
            )}

            {!loading && !error && jobs.length === 0 && (
              <div className="py-10 text-center text-slate-400 space-y-2">
                <Briefcase className="w-10 h-10 text-slate-600 mx-auto" />
                <p className="text-sm font-semibold text-slate-300">Nenhuma vaga aberta no momento.</p>
                <p className="text-xs text-slate-500">As oportunidades desta empresa podem ter sido preenchidas recentemente.</p>
              </div>
            )}

            {!loading &&
              jobs.map((job) => (
                <div
                  key={job.id}
                  className="p-4 rounded-2xl bg-[#070b0e] border border-[#182836] hover:border-amber-500/40 transition-all space-y-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        {job.title}
                        {job.openings_count > 1 && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/30">
                            {job.openings_count} vagas
                          </span>
                        )}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-[#182836] text-amber-300">
                          {CONTRACT_TYPE_LABELS[job.contract_type] || job.contract_type}
                        </span>
                        {job.published_at && (
                          <span className="text-[11px] text-slate-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            Publicada em {new Date(job.published_at).toLocaleDateString('pt-BR')}
                          </span>
                        )}
                      </div>
                    </div>

                    <a
                      href={`/api/v1/go/job/${job.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-950/50 flex items-center gap-1.5 shrink-0"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>Quero me candidatar</span>
                    </a>
                  </div>

                  {job.description && (
                    <p className="text-xs text-slate-300 leading-relaxed bg-[#0d151c] p-3 rounded-xl border border-[#182836]/60">
                      {job.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-1 border-t border-[#182836]/40 text-[11px]">
                    <span className="text-slate-500">
                      Candidatura direta no WhatsApp oficial da empresa
                    </span>
                    <button
                      type="button"
                      onClick={() => setReportJob({ id: job.id, title: job.title })}
                      className="text-slate-500 hover:text-red-400 transition-colors underline"
                    >
                      Denunciar vaga
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Modal de Denúncia */}
      {reportJob && (
        <ReportJobModal
          jobId={reportJob.id}
          jobTitle={reportJob.title}
          businessName={business.name}
          isOpen={true}
          onClose={() => setReportJob(null)}
        />
      )}
    </>
  );
}
