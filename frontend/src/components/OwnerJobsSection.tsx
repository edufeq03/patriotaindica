'use client';

import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  PlusCircle,
  Pause,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldAlert,
  X,
  Edit2,
  Info,
  Loader2,
  Trash2,
  Sparkles,
} from 'lucide-react';

interface JobOut {
  id: string;
  business_id: string;
  title: string;
  description?: string | null;
  contract_type: string;
  openings_count: number;
  status: 'pending_review' | 'active' | 'expired' | 'closed' | 'rejected';
  owner_paused: boolean;
  admin_hold: boolean;
  moderation_flags: string[];
  published_at?: string | null;
  expires_at?: string | null;
  renewed_count: number;
  close_reason?: string | null;
  created_at: string;
}

interface OwnerJobsSectionProps {
  businessId: string;
  businessName: string;
  businessStatus: string;
}

const CONTRACT_TYPE_OPTIONS = [
  { value: 'clt', label: 'CLT (Efetivo)' },
  { value: 'temporario', label: 'Temporário' },
  { value: 'meio_periodo', label: 'Meio Período' },
  { value: 'estagio', label: 'Estágio' },
  { value: 'aprendiz', label: 'Jovem Aprendiz' },
  { value: 'autonomo', label: 'Autônomo / PJ' },
];

const CLOSE_REASON_OPTIONS = [
  { value: 'hired_here', label: 'Contratamos pelo Patriota Indica' },
  { value: 'hired_other', label: 'Contratamos por outro canal' },
  { value: 'gave_up', label: 'Desistimos da contratação / Vaga cancelada' },
  { value: 'other', label: 'Outro motivo' },
];

export default function OwnerJobsSection({
  businessId,
  businessName,
  businessStatus,
}: OwnerJobsSectionProps) {
  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Modal de Criação / Edição
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingJob, setEditingJob] = useState<JobOut | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [contractType, setContractType] = useState('clt');
  const [openingsCount, setOpeningsCount] = useState(1);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Modal de Encerramento
  const [closingJob, setClosingJob] = useState<JobOut | null>(null);
  const [closeReason, setCloseReason] = useState('hired_here');
  const [closeLoading, setCloseLoading] = useState(false);

  // Carregar vagas
  const fetchJobs = async () => {
    if (!businessId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/owner/businesses/${businessId}/jobs`);
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Não foi possível carregar as vagas.');
      }
      const data = await res.json();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Erro ao consultar vagas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [businessId]);

  // Contadores
  const activeCount = jobs.filter((j) => j.status === 'active' && !j.owner_paused && !j.admin_hold).length;
  const pendingCount = jobs.filter((j) => j.status === 'pending_review').length;
  const pausedCount = jobs.filter((j) => j.owner_paused).length;
  const holdCount = jobs.filter((j) => j.admin_hold).length;
  const canCreate = jobs.filter((j) => ['active', 'pending_review'].includes(j.status)).length < 3;

  // Abrir modal de criação
  const handleOpenCreate = () => {
    setEditingJob(null);
    setTitle('');
    setDescription('');
    setContractType('clt');
    setOpeningsCount(1);
    setFormError(null);
    setShowCreateModal(true);
  };

  // Abrir modal de edição
  const handleOpenEdit = (job: JobOut) => {
    setEditingJob(job);
    setTitle(job.title);
    setDescription(job.description || '');
    setContractType(job.contract_type);
    setOpeningsCount(job.openings_count);
    setFormError(null);
    setShowCreateModal(true);
  };

  // Salvar Vaga (Criar ou Editar)
  const handleSaveJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError(null);

    try {
      const isEdit = Boolean(editingJob);
      const url = isEdit
        ? `/api/v1/owner/jobs/${editingJob!.id}`
        : `/api/v1/owner/businesses/${businessId}/jobs`;
      const method = isEdit ? 'PUT' : 'POST';

      const payload = {
        title: title.trim(),
        description: description.trim() || null,
        contract_type: contractType,
        openings_count: Number(openingsCount),
      };

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Erro ao salvar vaga de emprego.');
      }

      setShowCreateModal(false);
      setActionSuccess(
        isEdit
          ? 'Vaga atualizada com sucesso!'
          : data.status === 'active'
          ? 'Vaga publicada com sucesso e já está visível na vitrine!'
          : 'Vaga enviada com sucesso! Aguardando validação pela moderação.'
      );
      setTimeout(() => setActionSuccess(null), 5000);
      fetchJobs();
    } catch (err: any) {
      setFormError(err.message || 'Falha ao salvar anúncio de vaga.');
    } finally {
      setFormLoading(false);
    }
  };

  // Pausar / Reativar
  const handleTogglePause = async (job: JobOut) => {
    try {
      const res = await fetch(`/api/v1/owner/jobs/${job.id}/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pause: !job.owner_paused }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Não foi possível alterar o estado da vaga.');
      }
      setActionSuccess(
        job.owner_paused
          ? `Vaga "${job.title}" reativada com sucesso!`
          : `Vaga "${job.title}" pausada. Ela não será exibida na busca enquanto estiver pausada.`
      );
      setTimeout(() => setActionSuccess(null), 4000);
      fetchJobs();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Renovar Vaga (+30 dias)
  const handleRenewJob = async (job: JobOut) => {
    if (!confirm(`Deseja renovar a vaga "${job.title}" por mais 30 dias? (Renovação ${job.renewed_count + 1} de 2)`)) {
      return;
    }
    try {
      const res = await fetch(`/api/v1/owner/jobs/${job.id}/renew`, {
        method: 'POST',
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Não foi possível renovar a vaga.');
      }
      setActionSuccess(`Vaga "${job.title}" renovada por mais 30 dias!`);
      setTimeout(() => setActionSuccess(null), 4000);
      fetchJobs();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Confirmar Encerramento
  const handleConfirmClose = async () => {
    if (!closingJob) return;
    setCloseLoading(true);
    try {
      const res = await fetch(`/api/v1/owner/jobs/${closingJob.id}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ close_reason: closeReason }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'Erro ao encerrar a vaga.');
      }
      setClosingJob(null);
      setActionSuccess(`Vaga "${closingJob.title}" encerrada com sucesso.`);
      setTimeout(() => setActionSuccess(null), 4000);
      fetchJobs();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCloseLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Alerta de Feedback */}
      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-950/70 border border-emerald-500/50 text-emerald-300 text-xs flex items-center gap-2 shadow-lg animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-950/70 border border-red-500/50 text-red-300 text-xs flex items-center gap-2 shadow-lg">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Diretrizes Legais & Compliance (P1 da especificação) */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-500/10 via-[#0d151c] to-blue-500/10 border border-amber-500/30 flex items-start gap-3">
        <div className="p-2 rounded-xl bg-amber-500/15 text-amber-400 shrink-0 mt-0.5">
          <Info className="w-5 h-5" />
        </div>
        <div className="space-y-1 text-xs text-slate-300">
          <strong className="text-white block">
            Diretrizes para Divulgação de Vagas de Trabalho (Art. 5º CF / Lei 9.029/95)
          </strong>
          <p className="text-slate-400 leading-relaxed">
            Descreva apenas as <strong>atividades, horário, local e requisitos técnicos/profissionais</strong> da função. É estritamente vedado solicitar foto, idade (salvo aprendiz/estágio), sexo, estado civil, religião ou posicionamento político. Anúncios em desconformidade são bloqueados automaticamente pelo sistema.
          </p>
        </div>
      </div>

      {/* Cards de Métricas & Teto */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1">
          <span className="text-[11px] text-slate-400 block">Vagas Ativas</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-black text-emerald-400">{activeCount}</span>
            <span className="text-xs text-slate-500">/ 3 permitidas</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1">
          <span className="text-[11px] text-slate-400 block">Em Moderação</span>
          <span className="text-2xl font-black text-amber-400">{pendingCount}</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1">
          <span className="text-[11px] text-slate-400 block">Pausadas pelo Dono</span>
          <span className="text-2xl font-black text-blue-400">{pausedCount}</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1">
          <span className="text-[11px] text-slate-400 block">Sob Revisão (Hold)</span>
          <span className="text-2xl font-black text-red-400">{holdCount}</span>
        </div>
      </div>

      {/* Barra de Ação Superior */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-amber-400" />
            Oportunidades de Trabalho Cadastradas
          </h3>
          <p className="text-xs text-slate-400">
            Gerencie os anúncios de emprego da sua empresa na vitrine do Patriota Indica.
          </p>
        </div>

        <button
          type="button"
          disabled={!canCreate || businessStatus !== 'approved'}
          onClick={handleOpenCreate}
          className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-2 transition-all shadow-md shadow-amber-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
          title={
            businessStatus !== 'approved'
              ? 'Apenas empresas aprovadas na curadoria podem publicar vagas.'
              : !canCreate
              ? 'Limite de 3 vagas ativas ou em análise atingido.'
              : 'Criar nova vaga'
          }
        >
          <PlusCircle className="w-4 h-4" />
          <span>Publicar Nova Vaga</span>
        </button>
      </div>

      {/* Lista de Vagas */}
      {loading ? (
        <div className="p-12 rounded-2xl bg-[#0d151c] border border-[#182836] text-center text-slate-400 flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
          <span className="text-xs">Carregando anúncios de vagas...</span>
        </div>
      ) : jobs.length === 0 ? (
        <div className="p-12 rounded-2xl bg-[#0d151c] border border-[#182836] text-center space-y-3">
          <Briefcase className="w-12 h-12 text-slate-600 mx-auto" />
          <h4 className="text-sm font-bold text-white">Nenhuma vaga divulgada no momento</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Sua empresa pode cadastrar até 3 vagas ativas simultaneamente com validade de 30 dias cada.
          </p>
          {canCreate && businessStatus === 'approved' && (
            <div className="pt-2">
              <button
                type="button"
                onClick={handleOpenCreate}
                className="px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold inline-flex items-center gap-1.5"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                Cadastrar Primeira Vaga
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => {
            const isHold = job.admin_hold;
            const isPaused = job.owner_paused;
            const isActive = job.status === 'active' && !isPaused && !isHold;
            const isPending = job.status === 'pending_review';
            const isClosed = job.status === 'closed';
            const isExpired = job.status === 'expired';

            return (
              <div
                key={job.id}
                className="p-5 rounded-2xl bg-[#0d151c] border border-[#182836] hover:border-slate-700 transition-all space-y-4 shadow-lg"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-base font-bold text-white">{job.title}</h4>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-[#182836] text-amber-300">
                        {CONTRACT_TYPE_OPTIONS.find((c) => c.value === job.contract_type)?.label || job.contract_type}
                      </span>
                      {job.openings_count > 1 && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/30">
                          {job.openings_count} vagas
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                      <span>Criada em {new Date(job.created_at).toLocaleDateString('pt-BR')}</span>
                      {job.expires_at && (
                        <span>• Vence em {new Date(job.expires_at).toLocaleDateString('pt-BR')}</span>
                      )}
                      <span>• Renovações: {job.renewed_count}/2</span>
                    </div>
                  </div>

                  {/* Badges de Status */}
                  <div className="flex items-center gap-2">
                    {isHold && (
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-red-950 text-red-300 border border-red-500/40 flex items-center gap-1">
                        <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                        Bloqueio de Segurança (Hold)
                      </span>
                    )}

                    {!isHold && isPaused && (
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-blue-950 text-blue-300 border border-blue-500/40 flex items-center gap-1">
                        <Pause className="w-3.5 h-3.5 text-blue-400" />
                        Pausada por Você
                      </span>
                    )}

                    {!isHold && !isPaused && isActive && (
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        Ativa na Vitrine
                      </span>
                    )}

                    {isPending && (
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-amber-950 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-amber-400" />
                        Em Moderação
                      </span>
                    )}

                    {isClosed && (
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700 flex items-center gap-1">
                        Encerrada ({job.close_reason || 'Concluída'})
                      </span>
                    )}

                    {isExpired && (
                      <span className="text-xs font-bold px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700 flex items-center gap-1">
                        Expirada
                      </span>
                    )}
                  </div>
                </div>

                {job.description && (
                  <p className="text-xs text-slate-300 bg-[#070b0e] p-3 rounded-xl border border-[#182836] leading-relaxed">
                    {job.description}
                  </p>
                )}

                {/* Ações */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[#182836]">
                  <div className="text-[11px] text-slate-500">
                    Candidaturas chegam diretamente no WhatsApp oficial cadastrado.
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {/* Botão Pausar / Reativar */}
                    {!isHold && (job.status === 'active' || isPaused) && (
                      <button
                        type="button"
                        onClick={() => handleTogglePause(job)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                          isPaused
                            ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                            : 'bg-[#182836] hover:bg-[#253d52] text-amber-300'
                        }`}
                      >
                        {isPaused ? <Play className="w-3.5 h-3.5 fill-white" /> : <Pause className="w-3.5 h-3.5 fill-amber-300" />}
                        <span>{isPaused ? 'Reativar Vaga' : 'Pausar Vaga'}</span>
                      </button>
                    )}

                    {/* Botão Renovar (+30 dias) */}
                    {!isHold && job.renewed_count < 2 && ['active', 'expired'].includes(job.status) && (
                      <button
                        type="button"
                        onClick={() => handleRenewJob(job)}
                        className="px-3 py-1.5 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                        title="Estender a validade desta vaga por mais 30 dias"
                      >
                        <RotateCcw className="w-3.5 h-3.5 text-blue-400" />
                        <span>Renovar (+30 dias)</span>
                      </button>
                    )}

                    {/* Botão Editar */}
                    {!isHold && ['pending_review', 'active'].includes(job.status) && (
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(job)}
                        className="px-3 py-1.5 rounded-xl bg-[#070b0e] hover:bg-[#182836] text-slate-300 hover:text-white border border-[#182836] text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      >
                        <Edit2 className="w-3.5 h-3.5 text-amber-400" />
                        <span>Editar</span>
                      </button>
                    )}

                    {/* Botão Encerrar */}
                    {!isClosed && (
                      <button
                        type="button"
                        onClick={() => {
                          setClosingJob(job);
                          setCloseReason('hired_here');
                        }}
                        className="px-3 py-1.5 rounded-xl bg-[#070b0e] hover:bg-red-950/40 text-slate-400 hover:text-red-300 border border-[#182836] hover:border-red-500/30 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Encerrar Vaga</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* MODAL: CRIAR OU EDITAR VAGA */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg rounded-2xl bg-[#0d151c] border border-amber-500/30 p-6 shadow-2xl text-left space-y-4">
            <button
              onClick={() => setShowCreateModal(false)}
              className="absolute top-4 right-4 p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#182836] transition-colors"
              title="Fechar"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 border-b border-[#182836] pb-3">
              <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Briefcase className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  {editingJob ? 'Editar Anúncio de Vaga' : 'Publicar Nova Oportunidade'}
                </h3>
                <p className="text-xs text-slate-400">{businessName}</p>
              </div>
            </div>

            {formError && (
              <div className="p-3.5 rounded-xl bg-red-950/80 border border-red-500/50 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSaveJob} className="space-y-4">
              {/* Título do Cargo */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">
                    Título do Cargo / Função <span className="text-amber-400">*</span>
                  </label>
                  <span className={`text-[10px] ${title.length > 55 ? 'text-amber-400' : 'text-slate-500'}`}>
                    {title.length}/60
                  </span>
                </div>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={60}
                  placeholder="Ex: Eletricista Instalador, Vendedor, Mecânico..."
                  className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder-slate-500 focus:border-amber-500 outline-none"
                />
              </div>

              {/* Contrato e Vagas */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Tipo de Contrato</label>
                  <select
                    value={contractType}
                    onChange={(e) => setContractType(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
                  >
                    {CONTRACT_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">Número de Vagas</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={openingsCount}
                    onChange={(e) => setOpeningsCount(Math.max(1, Number(e.target.value)))}
                    className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
                  />
                </div>
              </div>

              {/* Descrição */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">
                    Descrição das Atividades e Requisitos
                  </label>
                  <span className={`text-[10px] ${description.length > 260 ? 'text-amber-400' : 'text-slate-500'}`}>
                    {description.length}/280
                  </span>
                </div>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={280}
                  rows={4}
                  placeholder="Descreva as funções, horário de trabalho, local e requisitos profissionais necessários..."
                  className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder-slate-500 focus:border-amber-500 outline-none resize-none leading-relaxed"
                />
              </div>

              {/* Caixa Educativa */}
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] leading-relaxed">
                💡 <strong>Atenção</strong>: Não inclua links, telefones ou e-mails no texto. O contato com os interessados ocorrerá diretamente através do WhatsApp oficial cadastrado na sua empresa.
              </div>

              {/* Botões */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#182836]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={formLoading || title.trim().length < 3}
                  className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold transition-all shadow-md shadow-amber-500/20 flex items-center gap-1.5 disabled:opacity-40"
                >
                  {formLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {formLoading
                    ? 'Salvando...'
                    : editingJob
                    ? 'Salvar Alterações'
                    : 'Publicar Vaga'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ENCERRAR VAGA */}
      {closingJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-2xl bg-[#0d151c] border border-amber-500/30 p-6 shadow-2xl text-left space-y-4">
            <button
              onClick={() => setClosingJob(null)}
              className="absolute top-4 right-4 p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-[#182836] transition-colors"
              title="Fechar"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 border-b border-[#182836] pb-3">
              <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Encerrar Vaga de Emprego</h3>
                <p className="text-xs text-slate-400 truncate max-w-[280px]">
                  {closingJob.title}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300">
              Ao encerrar, a vaga deixará de ser exibida na vitrine e candidatos não poderão mais acessá-la. Selecione o motivo do encerramento:
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Motivo</label>
              <select
                value={closeReason}
                onChange={(e) => setCloseReason(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
              >
                {CLOSE_REASON_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#182836]">
              <button
                type="button"
                onClick={() => setClosingJob(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={closeLoading}
                onClick={handleConfirmClose}
                className="px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition-all shadow-md shadow-red-950/50 flex items-center gap-1.5 disabled:opacity-50"
              >
                {closeLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {closeLoading ? 'Encerrando...' : 'Confirmar Encerramento'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
