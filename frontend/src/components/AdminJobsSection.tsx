'use client';

import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Search,
  Filter,
  Plus,
  Trash2,
  Power,
  RotateCcw,
  Loader2,
  X,
  FileText,
  Sliders,
  Sparkles,
} from 'lucide-react';

interface JobAdminOut {
  id: string;
  business_id: string;
  business_name: string;
  business_city: string;
  business_state: string;
  business_cnpj?: string | null;
  title: string;
  description?: string | null;
  contract_type: string;
  openings_count: number;
  status: 'pending_review' | 'active' | 'expired' | 'closed' | 'rejected';
  owner_paused: boolean;
  admin_hold: boolean;
  moderation_flags: string[];
  rejection_code?: string | null;
  published_at?: string | null;
  expires_at?: string | null;
  renewed_count: number;
  close_reason?: string | null;
  reports_count: number;
  created_at: string;
  updated_at: string;
}

interface ModerationTermOut {
  id: string;
  term_normalized: string;
  category: string;
  severity: string;
  match_type: string;
  active: boolean;
  created_at: string;
}

interface JobsMetrics {
  active: number;
  pending_review: number;
  admin_hold: number;
  closed: number;
  total: number;
}

export default function AdminJobsSection() {
  const [subTab, setSubTab] = useState<'queue' | 'terms'>('queue');

  // Estados da Fila
  const [jobs, setJobs] = useState<JobAdminOut[]>([]);
  const [metrics, setMetrics] = useState<JobsMetrics | null>(null);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [statusFilter, setStatusFilter] = useState('pending_review');
  const [flagFilter, setFlagFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Estados de Decisão
  const [selectedJob, setSelectedJob] = useState<JobAdminOut | null>(null);
  const [decisionAction, setDecisionAction] = useState<'approve' | 'reject' | 'hold' | 'release'>('approve');
  const [reasonCode, setReasonCode] = useState('conteudo_inadequado');
  const [decisionNote, setDecisionNote] = useState('');
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionFeedback, setDecisionFeedback] = useState<string | null>(null);

  // Estados de Termos de Moderação
  const [terms, setTerms] = useState<ModerationTermOut[]>([]);
  const [loadingTerms, setLoadingTerms] = useState(false);
  const [termCategoryFilter, setTermCategoryFilter] = useState('all');
  const [showNewTermModal, setShowNewTermModal] = useState(false);
  const [newTermText, setNewTermText] = useState('');
  const [newTermCategory, setNewTermCategory] = useState<'discriminacao' | 'conviccao' | 'golpe' | 'improprio' | 'review'>('discriminacao');
  const [newTermSeverity, setNewTermSeverity] = useState<'block' | 'review'>('block');
  const [newTermMatchType, setNewTermMatchType] = useState<'phrase' | 'word'>('phrase');
  const [newTermLoading, setNewTermLoading] = useState(false);
  const [termError, setTermError] = useState<string | null>(null);

  // Carregar métricas e fila
  const fetchMetrics = async () => {
    try {
      const res = await fetch('/api/v1/admin/jobs/metrics');
      if (res.ok) {
        setMetrics(await res.json());
      }
    } catch (err) {
      console.warn('Erro ao carregar métricas de vagas:', err);
    }
  };

  const fetchJobs = async () => {
    setLoadingJobs(true);
    try {
      let url = `/api/v1/admin/jobs?status_filter=${statusFilter}&limit=100`;
      if (flagFilter !== 'all') {
        url += `&flag=${flagFilter}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setJobs(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.warn('Erro ao carregar fila de vagas:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const fetchTerms = async () => {
    setLoadingTerms(true);
    try {
      let url = '/api/v1/admin/moderation-terms';
      if (termCategoryFilter !== 'all') {
        url += `?category=${termCategoryFilter}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setTerms(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.warn('Erro ao carregar termos:', err);
    } finally {
      setLoadingTerms(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    fetchJobs();
  }, [statusFilter, flagFilter]);

  useEffect(() => {
    if (subTab === 'terms') {
      fetchTerms();
    }
  }, [subTab, termCategoryFilter]);

  // Aplicar Decisão Administrativa
  const handleApplyDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJob) return;
    setDecisionLoading(true);

    try {
      const res = await fetch(`/api/v1/admin/jobs/${selectedJob.id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: decisionAction,
          reason_code: decisionAction === 'reject' ? reasonCode : undefined,
          note: decisionNote.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Erro ao registrar decisão de moderação.');
      }

      setDecisionFeedback(`Decisão "${decisionAction.toUpperCase()}" aplicada com sucesso à vaga "${selectedJob.title}".`);
      setSelectedJob(null);
      setDecisionNote('');
      setTimeout(() => setDecisionFeedback(null), 5000);
      fetchMetrics();
      fetchJobs();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setDecisionLoading(false);
    }
  };

  // Adicionar novo termo de moderação
  const handleCreateTerm = async (e: React.FormEvent) => {
    e.preventDefault();
    setNewTermLoading(true);
    setTermError(null);

    try {
      const res = await fetch('/api/v1/admin/moderation-terms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          term: newTermText.trim(),
          category: newTermCategory,
          severity: newTermSeverity,
          match_type: newTermMatchType,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Erro ao salvar novo termo de moderação.');
      }

      setShowNewTermModal(false);
      setNewTermText('');
      fetchTerms();
    } catch (err: any) {
      setTermError(err.message);
    } finally {
      setNewTermLoading(false);
    }
  };

  // Ativar / Desativar Termo
  const handleToggleTerm = async (term: ModerationTermOut) => {
    try {
      const res = await fetch(`/api/v1/admin/moderation-terms/${term.id}?active=${!term.active}`, {
        method: 'PATCH',
      });
      if (res.ok) {
        fetchTerms();
      }
    } catch (err) {
      alert('Falha ao alternar termo.');
    }
  };

  // Deletar Termo
  const handleDeleteTerm = async (termId: string) => {
    if (!confirm('Tem certeza que deseja remover este termo monitorado?')) return;
    try {
      const res = await fetch(`/api/v1/admin/moderation-terms/${termId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchTerms();
      }
    } catch (err) {
      alert('Falha ao remover termo.');
    }
  };

  const filteredJobs = jobs.filter((j) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      j.title.toLowerCase().includes(term) ||
      j.business_name.toLowerCase().includes(term) ||
      j.business_city.toLowerCase().includes(term) ||
      (j.description && j.description.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6">
      {/* Sub-navegação interna */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#182836] pb-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setSubTab('queue')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              subTab === 'queue'
                ? 'bg-amber-500 text-slate-950 shadow-md'
                : 'bg-[#0d151c] text-slate-400 hover:text-white border border-[#182836]'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Fila de Curadoria de Vagas</span>
            {metrics?.pending_review ? (
              <span className="px-1.5 py-0.2 rounded-full bg-red-600 text-white text-[10px]">
                {metrics.pending_review}
              </span>
            ) : null}
          </button>

          <button
            type="button"
            onClick={() => setSubTab('terms')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              subTab === 'terms'
                ? 'bg-blue-600 text-white shadow-md'
                : 'bg-[#0d151c] text-slate-400 hover:text-white border border-[#182836]'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>Termos de Moderação Automática</span>
          </button>
        </div>

        {subTab === 'queue' && (
          <button
            type="button"
            onClick={() => {
              fetchMetrics();
              fetchJobs();
            }}
            className="p-2 rounded-xl bg-[#0d151c] border border-[#182836] hover:border-amber-500/40 text-slate-400 hover:text-amber-400 text-xs flex items-center gap-1.5 transition-colors"
            title="Atualizar dados"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Atualizar</span>
          </button>
        )}
      </div>

      {/* Feedback de Sucesso */}
      {decisionFeedback && (
        <div className="p-4 rounded-xl bg-emerald-950/70 border border-emerald-500/50 text-emerald-300 text-xs flex items-center gap-2 shadow-lg animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span>{decisionFeedback}</span>
        </div>
      )}

      {/* ABA 1: FILA DE MODERAÇÃO */}
      {subTab === 'queue' && (
        <div className="space-y-6">
          {/* Métricas Rápidas */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1">
              <span className="text-[11px] text-slate-400 block">Vagas Ativas na Vitrine</span>
              <span className="text-2xl font-black text-emerald-400">{metrics?.active || 0}</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d151c] border border-amber-500/30 space-y-1">
              <span className="text-[11px] text-amber-300 block">Aguardando Revisão</span>
              <span className="text-2xl font-black text-amber-400">{metrics?.pending_review || 0}</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d151c] border border-red-500/30 space-y-1">
              <span className="text-[11px] text-red-300 block">Bloqueadas (Admin Hold)</span>
              <span className="text-2xl font-black text-red-400">{metrics?.admin_hold || 0}</span>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1">
              <span className="text-[11px] text-slate-400 block">Total de Anúncios</span>
              <span className="text-2xl font-black text-white">{metrics?.total || 0}</span>
            </div>
          </div>

          {/* Filtros e Busca */}
          <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                <Filter className="w-3.5 h-3.5" /> Status:
              </span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-1.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
              >
                <option value="pending_review">Pendentes de Moderação</option>
                <option value="active">Ativas</option>
                <option value="closed">Encerradas</option>
                <option value="all">Todas as Vagas</option>
              </select>

              <select
                value={flagFilter}
                onChange={(e) => setFlagFilter(e.target.value)}
                className="px-3 py-1.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
              >
                <option value="all">Todos os Estados</option>
                <option value="hold">Sob Hold / Denúncia</option>
                <option value="paused">Pausadas pelo Dono</option>
              </select>
            </div>

            <div className="relative min-w-[240px]">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filtrar por cargo, empresa ou cidade..."
                className="w-full pl-9 pr-3 py-1.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder-slate-500 focus:border-amber-500 outline-none"
              />
            </div>
          </div>

          {/* Tabela de Vagas */}
          {loadingJobs ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
              <span className="text-xs">Carregando fila de moderação...</span>
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="p-12 rounded-2xl bg-[#0d151c] border border-[#182836] text-center space-y-2">
              <CheckCircle2 className="w-12 h-12 text-emerald-500/60 mx-auto" />
              <h4 className="text-sm font-bold text-white">Fila limpa! Nenhuma vaga requer atenção no momento.</h4>
              <p className="text-xs text-slate-400">
                Todas as vagas submetidas estão em conformidade ou já foram avaliadas pela equipe.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredJobs.map((job) => (
                <div
                  key={job.id}
                  className="p-5 rounded-2xl bg-[#0d151c] border border-[#182836] hover:border-slate-700 transition-all space-y-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-base font-bold text-white">{job.title}</h4>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-[#182836] text-amber-300 uppercase">
                          {job.contract_type}
                        </span>
                        {job.admin_hold && (
                          <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-red-950 text-red-300 border border-red-500/40 flex items-center gap-1">
                            <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                            Admin Hold
                          </span>
                        )}
                        {job.reports_count > 0 && (
                          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 border border-red-500/40">
                            {job.reports_count} {job.reports_count === 1 ? 'denúncia' : 'denúncias'}
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                        <strong className="text-slate-200">{job.business_name}</strong>
                        <span>• {job.business_city} - {job.business_state}</span>
                        {job.business_cnpj && <span>• CNPJ: {job.business_cnpj}</span>}
                        <span>• Enviada em {new Date(job.created_at).toLocaleDateString('pt-BR')}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedJob(job);
                          setDecisionAction('approve');
                        }}
                        className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all shadow-md flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Aprovar</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setSelectedJob(job);
                          setDecisionAction('reject');
                        }}
                        className="px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition-all shadow-md flex items-center gap-1"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Rejeitar</span>
                      </button>

                      {job.admin_hold ? (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedJob(job);
                            setDecisionAction('release');
                          }}
                          className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-md flex items-center gap-1"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Liberar Hold</span>
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedJob(job);
                            setDecisionAction('hold');
                          }}
                          className="px-3 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-all shadow-md flex items-center gap-1"
                        >
                          <ShieldAlert className="w-3.5 h-3.5" />
                          <span>Bloquear (Hold)</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {job.description && (
                    <div className="p-3 rounded-xl bg-[#070b0e] border border-[#182836] text-xs text-slate-300 leading-relaxed">
                      {job.description}
                    </div>
                  )}

                  {/* Flags Detectadas */}
                  {job.moderation_flags && job.moderation_flags.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="text-amber-400 font-semibold flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> Termos Suspeitos Detectados:
                      </span>
                      {job.moderation_flags.map((flag, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono text-[11px]"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ABA 2: TERMOS DE MODERAÇÃO */}
      {subTab === 'terms' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Sliders className="w-5 h-5 text-blue-400" />
                Dicionário de Termos de Moderação Automática
              </h3>
              <p className="text-xs text-slate-400">
                Termos monitorados para triagem e bloqueio preventivo de discriminação, exigência de crença ou golpes.
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowNewTermModal(true);
                setTermError(null);
              }}
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center gap-1.5 transition-all shadow-md"
            >
              <Plus className="w-4 h-4" />
              <span>Adicionar Termo</span>
            </button>
          </div>

          {/* Filtro por Categoria */}
          <div className="flex flex-wrap gap-2">
            {['all', 'discriminacao', 'conviccao', 'golpe', 'improprio', 'review'].map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setTermCategoryFilter(cat)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition-colors ${
                  termCategoryFilter === cat
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-[#0d151c] text-slate-400 hover:text-white border border-[#182836]'
                }`}
              >
                {cat === 'all' ? 'Todas as Categorias' : cat}
              </button>
            ))}
          </div>

          {/* Lista de Termos */}
          {loadingTerms ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
              <span className="text-xs">Carregando termos...</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {terms.map((term) => (
                <div
                  key={term.id}
                  className={`p-3.5 rounded-xl bg-[#0d151c] border transition-all flex items-center justify-between gap-3 ${
                    term.active ? 'border-[#182836]' : 'border-zinc-800 opacity-60'
                  }`}
                >
                  <div className="space-y-1">
                    <span className="font-mono text-xs font-bold text-white block">
                      &quot;{term.term_normalized}&quot;
                    </span>
                    <div className="flex items-center gap-1.5 text-[10px]">
                      <span className="px-1.5 py-0.2 rounded bg-[#182836] text-blue-300 uppercase">
                        {term.category}
                      </span>
                      <span
                        className={`px-1.5 py-0.2 rounded ${
                          term.severity === 'block'
                            ? 'bg-red-500/20 text-red-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}
                      >
                        {term.severity}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleToggleTerm(term)}
                      className={`p-1.5 rounded-lg border text-xs transition-colors ${
                        term.active
                          ? 'border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10'
                          : 'border-slate-700 text-slate-500 hover:text-white'
                      }`}
                      title={term.active ? 'Desativar monitoramento' : 'Ativar monitoramento'}
                    >
                      <Power className="w-3.5 h-3.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDeleteTerm(term.id)}
                      className="p-1.5 rounded-lg border border-slate-700 text-slate-500 hover:text-red-400 hover:border-red-500/40 transition-colors"
                      title="Excluir termo"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL: DECISÃO DE CURADORIA */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg rounded-2xl bg-[#0d151c] border border-amber-500/30 p-6 shadow-2xl text-left space-y-4">
            <button
              onClick={() => setSelectedJob(null)}
              className="absolute top-4 right-4 p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#182836] transition-colors"
              title="Fechar"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 border-b border-[#182836] pb-3">
              <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white capitalize">
                  {decisionAction === 'approve' && 'Aprovar Vaga para Vitrine'}
                  {decisionAction === 'reject' && 'Rejeitar Anúncio de Vaga'}
                  {decisionAction === 'hold' && 'Aplicar Bloqueio de Segurança (Hold)'}
                  {decisionAction === 'release' && 'Liberar Vaga sob Bloqueio'}
                </h3>
                <p className="text-xs text-slate-400">
                  {selectedJob.title} • {selectedJob.business_name}
                </p>
              </div>
            </div>

            <form onSubmit={handleApplyDecision} className="space-y-4">
              {decisionAction === 'reject' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Motivo da Recusa</label>
                  <select
                    value={reasonCode}
                    onChange={(e) => setReasonCode(e.target.value)}
                    className="w-full px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-red-500 outline-none"
                  >
                    <option value="discriminacao">Discriminação (exigência de foto, idade, sexo)</option>
                    <option value="conviccao">Exigência de convicção religiosa ou política</option>
                    <option value="golpe">Cobrança de taxa ou anúncio suspeito de golpe</option>
                    <option value="conteudo_inadequado">Conteúdo inadequado ou fora das diretrizes</option>
                  </select>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Justificativa / Parecer do Curador (gravado no log de auditoria)
                </label>
                <textarea
                  value={decisionNote}
                  onChange={(e) => setDecisionNote(e.target.value)}
                  rows={3}
                  placeholder="Descreva as orientações ou observações para auditoria..."
                  className="w-full px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder-slate-500 focus:border-amber-500 outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#182836]">
                <button
                  type="button"
                  onClick={() => setSelectedJob(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={decisionLoading}
                  className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-md flex items-center gap-1.5 ${
                    decisionAction === 'approve' || decisionAction === 'release'
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                      : 'bg-red-600 hover:bg-red-500 text-white'
                  }`}
                >
                  {decisionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {decisionLoading ? 'Processando...' : 'Confirmar Decisão'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: NOVO TERMO DE MODERAÇÃO */}
      {showNewTermModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-2xl bg-[#0d151c] border border-blue-500/30 p-6 shadow-2xl text-left space-y-4">
            <button
              onClick={() => setShowNewTermModal(false)}
              className="absolute top-4 right-4 p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#182836] transition-colors"
              title="Fechar"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 border-b border-[#182836] pb-3">
              <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <Sliders className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Adicionar Termo Monitorado</h3>
                <p className="text-xs text-slate-400">Moderação Automática de Anúncios</p>
              </div>
            </div>

            {termError && (
              <div className="p-3 rounded-xl bg-red-950/80 border border-red-500/50 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                <span>{termError}</span>
              </div>
            )}

            <form onSubmit={handleCreateTerm} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Termo ou Expressão</label>
                <input
                  type="text"
                  required
                  value={newTermText}
                  onChange={(e) => setNewTermText(e.target.value)}
                  placeholder="Ex: boa aparencia, taxa de inscricao..."
                  className="w-full px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder-slate-500 focus:border-blue-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Categoria</label>
                  <select
                    value={newTermCategory}
                    onChange={(e) => setNewTermCategory(e.target.value as any)}
                    className="w-full px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-blue-500 outline-none"
                  >
                    <option value="discriminacao">Discriminação</option>
                    <option value="conviccao">Convicção</option>
                    <option value="golpe">Golpe / Fraude</option>
                    <option value="improprio">Impróprio</option>
                    <option value="review">Revisão Humana</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Ação / Severidade</label>
                  <select
                    value={newTermSeverity}
                    onChange={(e) => setNewTermSeverity(e.target.value as any)}
                    className="w-full px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-blue-500 outline-none"
                  >
                    <option value="block">Bloqueio Automático (422)</option>
                    <option value="review">Enviar para Moderação Humana</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#182836]">
                <button
                  type="button"
                  onClick={() => setShowNewTermModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={newTermLoading || newTermText.trim().length < 2}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50"
                >
                  {newTermLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {newTermLoading ? 'Adicionando...' : 'Cadastrar Termo'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
