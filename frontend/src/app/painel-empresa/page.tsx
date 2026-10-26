'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { 
  Building2, 
  MessageCircle, 
  Phone, 
  Eye, 
  Clock, 
  TrendingUp, 
  Pause, 
  Play, 
  ShieldAlert, 
  ShieldCheck, 
  CheckCircle2, 
  Save, 
  ArrowLeft, 
  ExternalLink,
  Sliders,
  AlertTriangle,
  Award,
  Star,
  MapPin,
  Calendar,
  Lock,
  FileText
} from 'lucide-react';
import { Suspense } from 'react';
import { INITIAL_BUSINESSES } from '@/lib/mockData';
import { Business } from '@/lib/types';
import ManifestoModal from '@/components/ManifestoModal';

export default function BusinessDashboardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#070b0e] text-slate-400 p-8 text-center text-xs">Carregando painel da empresa...</div>}>
      <BusinessDashboardContent />
    </Suspense>
  );
}

function BusinessDashboardContent() {
  const searchParams = useSearchParams();
  const requestedBizId = searchParams?.get('bizId');

  // Modal da Carta de Princípios
  const [showManifestoModal, setShowManifestoModal] = useState(false);

  // Empresa ativa no painel (padrão: Silva Instalações ou a primeira aprovada)
  const [selectedBizId, setSelectedBizId] = useState<string>(
    requestedBizId || INITIAL_BUSINESSES[0].id
  );

  const business = INITIAL_BUSINESSES.find((b) => b.id === selectedBizId) || INITIAL_BUSINESSES[0];

  // Estado do anúncio (Pausado / Ativo)
  const [isPaused, setIsPaused] = useState<boolean>(false);

  // Form State
  const [description, setDescription] = useState(business.description);
  const [instagram, setInstagram] = useState(business.instagram || '');
  const [website, setWebsite] = useState(business.website || '');
  const [operatingHours, setOperatingHours] = useState('Segunda a Sexta: 08h às 18h | Sábados: 08h às 13h');

  // Campos sensíveis (reabrem triagem)
  const [whatsapp, setWhatsapp] = useState(business.whatsapp);
  const [neighborhood, setNeighborhood] = useState(business.neighborhood);

  // Estado de aviso e salvamento
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [sensitiveWarning, setSensitiveWarning] = useState<boolean>(false);
  const [currentStatus, setCurrentStatus] = useState<string>(business.status);

  // Manipular salvamento
  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();

    // Se alterou WhatsApp ou bairro, reabre triagem (Regra da Seção 7.2 item 4)
    if (whatsapp !== business.whatsapp || neighborhood !== business.neighborhood) {
      setCurrentStatus('pending_review');
      setSensitiveWarning(true);
      setSaveSuccess(
        'Perfil atualizado! Por conter alteração de WhatsApp ou Endereço, o status reabriu para "Em Análise" na triagem por segurança.'
      );
    } else {
      setSaveSuccess('Alterações salvas com sucesso no seu perfil público!');
      setSensitiveWarning(false);
    }

    setTimeout(() => setSaveSuccess(null), 5000);
  };

  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col font-sans selection:bg-amber-500 selection:text-black">
      {/* Top Navbar */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center gap-2 text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-[#070b0e] border border-[#182836] hover:border-amber-500/50 text-slate-300 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Ver Marketplace
            </Link>
            <div className="h-5 w-[1px] bg-[#182836]" />
            <div className="flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-amber-950/80 border border-amber-500/40 flex items-center justify-center text-amber-400 font-bold text-xs">
                PE
              </span>
              <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                Painel da Empresa
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  Lojista / Prestador
                </span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedBizId}
              onChange={(e) => {
                setSelectedBizId(e.target.value);
                const newB = INITIAL_BUSINESSES.find(b => b.id === e.target.value);
                if (newB) {
                  setDescription(newB.description);
                  setWhatsapp(newB.whatsapp);
                  setNeighborhood(newB.neighborhood);
                  setCurrentStatus(newB.status);
                }
              }}
              className="px-3 py-1.5 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
            >
              {INITIAL_BUSINESSES.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 py-8 flex-1 w-full space-y-6">
        {/* Banner de Status e Controle */}
        <div className="p-6 rounded-2xl bg-[#0d151c] border border-[#182836] shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {business.category_name}
              </span>

              {currentStatus === 'approved' && !isPaused && (
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  Anúncio Ativo na Busca
                </span>
              )}

              {isPaused && (
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                  <Pause className="w-3.5 h-3.5 text-amber-400" />
                  Anúncio Pausado pelo Dono
                </span>
              )}

              {currentStatus === 'pending_review' && (
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  Reanálise em Andamento
                </span>
              )}
            </div>

            <h2 className="text-2xl font-black text-white">{business.name}</h2>
            <p className="text-xs text-slate-400 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-amber-400" />
              {business.neighborhood}, {business.city} - {business.state}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Toggle de Pausa do Anúncio (Seção 7.2 item 5) */}
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all ${
                isPaused
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md'
                  : 'bg-[#182836] hover:bg-[#253d52] text-amber-300 border border-amber-500/30'
              }`}
            >
              {isPaused ? <Play className="w-4 h-4 fill-white" /> : <Pause className="w-4 h-4 fill-amber-300" />}
              {isPaused ? 'Reativar Anúncio' : 'Pausar Anúncio'}
            </button>

            <Link
              href={`/${business.city.toLowerCase()}-${business.state.toLowerCase()}/${business.category_slug}/${business.slug}`}
              target="_blank"
              className="px-4 py-2.5 rounded-xl bg-[#070b0e] hover:bg-[#121e29] border border-[#182836] text-xs font-medium text-slate-200 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              Ver Perfil Público
              <ExternalLink className="w-3.5 h-3.5 text-amber-400" />
            </Link>
          </div>
        </div>

        {/* Card de Signatária da Carta de Princípios */}
        <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-950/25 via-[#0d151c] to-emerald-950/25 border border-amber-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <p className="font-bold text-white text-xs sm:text-sm flex items-center gap-2">
                Empresa Signatária Oficial • Patriota Indica
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono">
                  {business.manifesto_version || 'v1.0-2026'}
                </span>
              </p>
              <p className="text-slate-400 text-xs">
                Seu negócio ostenta publicamente o selo de honra da Livre Iniciativa, Propriedade Privada e Ética Cristã/Ocidental.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowManifestoModal(true)}
            className="px-3.5 py-1.5 rounded-xl border border-amber-500/40 text-amber-300 hover:bg-amber-500/15 text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" />
            Ver Carta Completa
          </button>
        </div>

        {/* Notificações e Alertas */}
        {saveSuccess && (
          <div className="p-4 rounded-xl bg-emerald-950/70 border border-emerald-500/60 text-emerald-300 text-xs flex items-center gap-2 shadow-lg animate-in fade-in">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span>{saveSuccess}</span>
          </div>
        )}

        {/* Grid de Métricas de Conversão */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-[#0d151c] border border-emerald-900/50 space-y-1 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Cliques no WhatsApp</span>
              <MessageCircle className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-3xl font-black text-emerald-400">142</p>
            <span className="text-[11px] text-emerald-500/80 font-medium">Conversões diretas no mês</span>
          </div>

          <div className="p-5 rounded-2xl bg-[#0d151c] border border-blue-900/50 space-y-1 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Ligações Telefônicas</span>
              <Phone className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-3xl font-black text-blue-400">18</p>
            <span className="text-[11px] text-blue-500/80 font-medium">Cliques em telefone fixo</span>
          </div>

          <div className="p-5 rounded-2xl bg-[#0d151c] border border-amber-900/50 space-y-1 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Visualizações de Perfil</span>
              <Eye className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-3xl font-black text-amber-400">489</p>
            <span className="text-[11px] text-amber-500/80 font-medium">Visualizações na busca local</span>
          </div>

          <div className="p-5 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-1 shadow-md">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Taxa de Conversão</span>
              <TrendingUp className="w-4 h-4 text-amber-300" />
            </div>
            <p className="text-3xl font-black text-white">29.0%</p>
            <span className="text-[11px] text-slate-400 font-medium">Cliques / Visualizações</span>
          </div>
        </div>

        {/* Formulário de Edição do Perfil da Empresa */}
        <div className="p-6 md:p-8 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#182836] gap-2">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Sliders className="w-5 h-5 text-amber-400" />
                Editar Informações da Empresa
              </h3>
              <p className="text-xs text-slate-400">
                Mantenha suas especialidades, horários e canais de contato sempre atualizados.
              </p>
            </div>
          </div>

          {/* Alerta de Segurança e Curadoria (Regra Inegociável da Seção 7.2) */}
          <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-300 text-xs space-y-1.5 leading-relaxed">
            <div className="flex items-center gap-2 font-bold text-amber-400">
              <ShieldAlert className="w-4 h-4 shrink-0" />
              <span>Regra de Curadoria e Proteção ao Consumidor:</span>
            </div>
            <p>
              Você pode editar <strong>descrição, especialidades e redes sociais</strong> livremente a qualquer momento.
              No entanto, alterações em <strong>WhatsApp, CNPJ ou Endereço físico</strong> reabrem automaticamente a
              análise na triagem administrativa para garantir a veracidade perante os consumidores.
            </p>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-5 text-xs">
            {/* Seção 1: Descrição e Horários (Livre) */}
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Star className="w-3.5 h-3.5 text-amber-400" />
                Apresentação e Horários (Edição Imediata)
              </h4>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Descrição e Diferenciais *</label>
                <textarea
                  required
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Horário de Funcionamento</label>
                  <input
                    type="text"
                    value={operatingHours}
                    onChange={(e) => setOperatingHours(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Instagram (@usuario)</label>
                  <input
                    type="text"
                    value={instagram}
                    onChange={(e) => setInstagram(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Website Oficial</label>
                  <input
                    type="text"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Seção 2: Campos Sensíveis (Reabrem Triagem) */}
            <div className="space-y-4 pt-4 border-t border-[#182836]">
              <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-amber-400" />
                Dados Cadastrais Críticos (Requerem Nova Triagem se Alterados)
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1 flex items-center justify-between">
                    <span>WhatsApp de Atendimento</span>
                    <span className="text-[10px] text-amber-400">Sensível</span>
                  </label>
                  <input
                    required
                    type="text"
                    value={whatsapp}
                    onChange={(e) => setWhatsapp(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1 flex items-center justify-between">
                    <span>Bairro / Região</span>
                    <span className="text-[10px] text-amber-400">Sensível</span>
                  </label>
                  <input
                    required
                    type="text"
                    value={neighborhood}
                    onChange={(e) => setNeighborhood(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                className="w-full sm:w-auto px-8 py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-black text-xs md:text-sm transition-all shadow-lg shadow-amber-950/50 flex items-center justify-center gap-2"
              >
                <Save className="w-4 h-4 fill-black" />
                Salvar Alterações do Perfil
              </button>
            </div>
          </form>
        </div>
      </main>

      {/* Modal da Carta de Princípios e Valores da Liberdade */}
      <ManifestoModal
        isOpen={showManifestoModal}
        onClose={() => setShowManifestoModal(false)}
      />
    </div>
  );
}
