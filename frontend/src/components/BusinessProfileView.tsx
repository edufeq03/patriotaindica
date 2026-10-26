'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeft, 
  CheckCircle2, 
  ShieldCheck, 
  MapPin, 
  Phone, 
  MessageCircle, 
  Globe, 
  Camera, 
  AlertTriangle, 
  Building2, 
  Clock, 
  Navigation, 
  FileCheck, 
  Star, 
  KeyRound, 
  X, 
  Check, 
  Lock,
  Sparkles,
  ArrowRight,
  FileText
} from 'lucide-react';
import { Business } from '@/lib/types';
import ManifestoModal from '@/components/ManifestoModal';

interface Props {
  business: Business;
  city: string;
  category: string;
  slug: string;
}

export default function BusinessProfileView({ business, city, category, slug }: Props) {
  const router = useRouter();

  // Modal da Carta de Princípios
  const [showManifestoModal, setShowManifestoModal] = useState(false);

  // Modal de Denúncia
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportReason, setReportReason] = useState('Violação da Carta de Princípios');
  const [reportDetails, setReportDetails] = useState('');
  const [reportSuccess, setReportSuccess] = useState(false);

  // Estado do Modal de Reivindicação (Canal D com OTP 100% server-side - C4)
  const [showClaimModal, setShowClaimModal] = useState(false);
  const [claimStep, setClaimStep] = useState<'confirm' | 'otp' | 'success'>('confirm');
  const [otpCode, setOtpCode] = useState('');
  const [otpError, setOtpError] = useState<string | null>(null);
  const [otpLoading, setOtpLoading] = useState(false);
  const [maskedPhone, setMaskedPhone] = useState('');

  // Disparar envio de código OTP no servidor
  const handleSendOtp = async () => {
    setOtpLoading(true);
    setOtpError(null);
    try {
      const res = await fetch(`/api/v1/claim/${business.id}/request-otp`, {
        method: 'POST',
      });
      const data = await res.json().catch(() => null);
      if (res.ok) {
        setMaskedPhone(data?.masked_phone || '');
        setClaimStep('otp');
      } else {
        setOtpError(data?.detail || 'Falha ao solicitar código de confirmação.');
      }
    } catch {
      setOtpError('Não foi possível conectar ao servidor para envio do código.');
    } finally {
      setOtpLoading(false);
    }
  };

  // Validar código OTP no servidor
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setOtpLoading(true);
    setOtpError(null);
    try {
      const res = await fetch(`/api/v1/claim/${business.id}/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: otpCode.trim() }),
      });
      const data = await res.json().catch(() => null);
      if (res.ok) {
        setClaimStep('success');
      } else {
        setOtpError(data?.detail || 'Código de confirmação incorreto.');
      }
    } catch {
      setOtpError('Erro ao validar código. Tente novamente.');
    } finally {
      setOtpLoading(false);
    }
  };


  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col font-sans selection:bg-amber-500 selection:text-black">
      {/* Top Navbar */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-amber-300 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para busca
          </Link>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs px-3 py-1 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 shadow-sm">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Empresa Curada & Aprovada
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Container */}
      <main className="max-w-5xl mx-auto px-4 py-8 flex-1 w-full space-y-8">
        {/* Breadcrumb com Realces Dourados */}
        <nav className="text-xs text-slate-400 flex items-center gap-2">
          <Link href="/" className="hover:text-amber-300">Início</Link>
          <span>/</span>
          <span className="capitalize">{business.city} - {business.state}</span>
          <span>/</span>
          <span className="capitalize">{business.category_name}</span>
          <span>/</span>
          <span className="text-amber-400 font-semibold">{business.name}</span>
        </nav>

        {/* Hero Card */}
        <div className="relative rounded-2xl overflow-hidden border border-[#182836] bg-[#0d151c] p-6 md:p-8 backdrop-blur-sm shadow-2xl">
          {business.banner_url && (
            <div 
              className="absolute inset-0 opacity-15 bg-cover bg-center"
              style={{ backgroundImage: `url(${business.banner_url})` }}
            />
          )}
          <div className="relative z-10 space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    {business.category_name}
                  </span>
                  {business.accepted_manifesto && (
                    <button
                      onClick={() => setShowManifestoModal(true)}
                      className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 shadow-sm hover:bg-amber-500/25 transition-colors cursor-pointer"
                      title="Empresa Signatária da Carta de Princípios da Liberdade (Clique para ler)"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                      Signatária da Carta de Princípios
                    </button>
                  )}
                  {business.is_verified && (
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-950/80 text-blue-300 border border-blue-500/40 flex items-center gap-1 shadow-sm">
                      <CheckCircle2 className="w-3 h-3 text-blue-400" />
                      Selo de Verificação
                    </span>
                  )}
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-950/70 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                    Curadoria Oficial
                  </span>
                </div>
                <h1 className="text-2xl md:text-4xl font-black tracking-tight text-white">
                  {business.name}
                </h1>
                <p className="text-sm md:text-base text-slate-300 flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-amber-400 shrink-0" />
                  {business.neighborhood}, {business.city} - {business.state}
                  {business.show_full_address && business.street && (
                    <span className="text-slate-400 font-mono">({business.street}, {business.number})</span>
                  )}
                </p>
              </div>

              {/* Botão de Contato Principal (Verde Esmeralda) */}
              <div className="w-full md:w-auto">
                <a
                  href={(() => {
                    const clean = (business.whatsapp || '').replace(/\D/g, '');
                    const withDdi = clean.startsWith('55') ? clean : `55${clean}`;
                    const text = encodeURIComponent(`Olá! Vi seu anúncio no Patriota Indica e gostaria de solicitar informações sobre ${business.name}.`);
                    return clean ? `https://wa.me/${withDdi}?text=${text}` : `/go/whatsapp/${business.id}`;
                  })()}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => {
                    fetch(`/api/v1/go/whatsapp/${business.id}`, { keepalive: true }).catch(() => {});
                  }}
                  className="w-full md:w-auto flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-lg shadow-emerald-950/60 transition-all text-sm md:text-base border border-amber-400/30"
                >
                  <MessageCircle className="w-5 h-5 fill-current" />
                  Conversar no WhatsApp
                </a>
              </div>
            </div>

            {/* Atendimento e Raio */}
            <div className="pt-4 border-t border-[#182836] flex flex-wrap gap-4 text-xs md:text-sm text-slate-300">
              <div className="flex items-center gap-2 bg-[#070b0e] px-3.5 py-2 rounded-xl border border-[#182836]">
                <Navigation className="w-4 h-4 text-emerald-400" />
                <span>
                  Modo de Atendimento:{' '}
                  <strong className="text-white">
                    {business.service_mode === 'at_customer'
                      ? `Atende a domicílio (Raio de ${business.service_radius_km || 25} km)`
                      : business.service_mode === 'at_location'
                      ? 'Atendimento presencial no estabelecimento'
                      : `Presencial e a domicílio (Raio de ${business.service_radius_km || 15} km)`}
                  </strong>
                </span>
              </div>
              <div className="flex items-center gap-2 bg-[#070b0e] px-3.5 py-2 rounded-xl border border-[#182836]">
                <Clock className="w-4 h-4 text-amber-400" />
                <span>Resposta Rápida no WhatsApp</span>
              </div>
            </div>
          </div>
        </div>

        {/* Informações Detalhadas em Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Coluna 1 & 2: Descrição e Curadoria */}
          <div className="md:col-span-2 space-y-6">
            <section className="bg-[#0d151c] border border-[#182836] rounded-2xl p-6 space-y-4 shadow-xl">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Building2 className="w-5 h-5 text-amber-400" />
                Sobre a Empresa e Especialidades
              </h2>
              <p className="text-slate-300 leading-relaxed text-sm md:text-base whitespace-pre-line">
                {business.description}
              </p>
            </section>

            {/* Checklist de Curadoria (Transparência com o Consumidor) */}
            <section className="bg-[#0d151c] border border-[#182836] rounded-2xl p-6 space-y-4 shadow-xl">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                Critérios de Triagem e Qualidade Aprovados
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs md:text-sm">
                <div 
                  onClick={() => setShowManifestoModal(true)}
                  className="flex items-center gap-2.5 p-3 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-200 cursor-pointer hover:bg-amber-950/50 transition-colors shadow-sm"
                  title="Clique para ler a Carta de Princípios"
                >
                  <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>Subscrição à Carta de Princípios ({business.manifesto_version || 'v1.0-2026'})</span>
                </div>
                <div className="flex items-center gap-2.5 p-3 rounded-xl bg-[#070b0e] border border-emerald-950/60 text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Situação Cadastral Ativa (Receita)</span>
                </div>
                <div className="flex items-center gap-2.5 p-3 rounded-xl bg-[#070b0e] border border-emerald-950/60 text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>WhatsApp de Atendimento Verificado</span>
                </div>
                <div className="flex items-center gap-2.5 p-3 rounded-xl bg-[#070b0e] border border-emerald-950/60 text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Endereço Georreferenciado na Cidade</span>
                </div>
              </div>
            </section>
          </div>

          {/* Coluna 3: Contatos e Ações */}
          <div className="space-y-6">
            <div className="bg-[#0d151c] border border-[#182836] rounded-2xl p-6 space-y-4 shadow-xl">
              <h3 className="text-base font-bold text-white">Canais de Atendimento</h3>
              <div className="space-y-2.5">
                <a
                  href={`/go/whatsapp/${business.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl bg-emerald-950/40 border border-emerald-700/50 hover:bg-emerald-900/40 text-emerald-300 transition-colors text-sm font-semibold"
                >
                  <span className="flex items-center gap-2">
                    <MessageCircle className="w-4 h-4 text-emerald-400" />
                    WhatsApp
                  </span>
                  <span className="text-xs bg-emerald-900/60 px-2 py-0.5 rounded text-emerald-200">Mensagem Direta</span>
                </a>

                {business.phone && (
                  <a
                    href={`/go/phone/${business.id}`}
                    className="flex items-center justify-between p-3 rounded-xl bg-[#070b0e] border border-[#182836] hover:bg-[#121e29] text-slate-300 transition-colors text-sm font-medium"
                  >
                    <span className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-blue-400" />
                      Telefone Fixo
                    </span>
                    <span className="text-xs text-slate-400">Ligar</span>
                  </a>
                )}

                {business.website && (
                  <a
                    href={`/go/website/${business.id}`}
                    target="_blank"
                    rel="nofollow noopener noreferrer ugc"
                    className="flex items-center justify-between p-3 rounded-xl bg-[#070b0e] border border-[#182836] hover:bg-[#121e29] text-slate-300 transition-colors text-sm font-medium"
                  >
                    <span className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-purple-400" />
                      Website Oficial
                    </span>
                    <span className="text-xs text-slate-400">Visitar</span>
                  </a>
                )}

                {business.instagram && (
                  <a
                    href={`https://instagram.com/${business.instagram}`}
                    target="_blank"
                    rel="nofollow noopener noreferrer ugc"
                    className="flex items-center justify-between p-3 rounded-xl bg-[#070b0e] border border-[#182836] hover:bg-[#121e29] text-slate-300 transition-colors text-sm font-medium"
                  >
                    <span className="flex items-center gap-2">
                      <Camera className="w-4 h-4 text-pink-400" />
                      Instagram
                    </span>
                    <span className="text-xs text-slate-400">@{business.instagram}</span>
                  </a>
                )}
              </div>
            </div>

            {/* Reivindicar Perfil (Canal D com OTP) & Denúncia */}
            <div className="bg-[#0d151c]/70 border border-amber-500/30 rounded-2xl p-5 space-y-4 shadow-xl">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
                  <KeyRound className="w-4 h-4" />
                  <span>Você é o proprietário?</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Reivindique o controle deste perfil gratuitamente para editar fotos, horários e acompanhar cliques de contato.
                </p>
                <button
                  onClick={() => {
                    setShowClaimModal(true);
                    setClaimStep('confirm');
                  }}
                  className="w-full py-2.5 px-4 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/50 text-amber-300 font-bold text-xs transition-colors flex items-center justify-center gap-2"
                >
                  <FileCheck className="w-4 h-4 text-amber-400" />
                  Reivindicar este perfil via WhatsApp (Canal D)
                </button>
              </div>

              <div className="pt-3 border-t border-[#182836] flex items-center justify-between text-xs text-slate-400">
                <span>Suspeita de golpe ou dados incorretos?</span>
                <button
                  onClick={() => setShowReportModal(true)}
                  className="text-amber-400/90 hover:underline flex items-center gap-1"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Denunciar
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Modal: Canal D - Reivindicação de Perfil com OTP de WhatsApp */}
      {showClaimModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="bg-[#0d151c] border border-amber-500/40 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl relative">
            <button
              onClick={() => setShowClaimModal(false)}
              className="absolute right-4 top-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="space-y-1">
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
                Canal D: Confirmação de Posse
              </span>
              <h2 className="text-xl font-bold text-white">Reivindicar {business.name}</h2>
              <p className="text-xs text-slate-400">
                Para sua segurança, enviaremos um código de autenticação via WhatsApp para o número cadastrado da empresa.
              </p>
            </div>

            {/* Passo 1: Confirmar envio */}
            {claimStep === 'confirm' && (
              <div className="space-y-4 text-xs">
                <div className="p-4 rounded-xl bg-[#070b0e] border border-[#182836] space-y-2">
                  <span className="text-slate-400">Número de WhatsApp cadastrado:</span>
                  <p className="font-mono text-sm text-emerald-400 font-bold">
                    +55 {business.whatsapp.slice(0, 2)} *****-{business.whatsapp.slice(-4)}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Você deve ter acesso a esta linha para receber o código de 6 dígitos.
                  </p>
                </div>

                <button
                  onClick={handleSendOtp}
                  disabled={otpLoading}
                  className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-extrabold transition-colors shadow-lg shadow-amber-950/40 flex items-center justify-center gap-2"
                >
                  <MessageCircle className="w-4 h-4 fill-black" />
                  {otpLoading ? 'Enviando código via WhatsApp...' : 'Enviar Código OTP para este WhatsApp'}
                </button>
                {otpError && (
                  <p className="text-red-400 text-[11px] text-center mt-2">{otpError}</p>
                )}
              </div>
            )}

            {/* Passo 2: Digitar Código OTP */}
            {claimStep === 'otp' && (
              <form onSubmit={handleVerifyOtp} className="space-y-4 text-xs">
                {/* Feedback de envio server-side seguro */}
                <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Código de Confirmação Enviado com Sucesso</span>
                  </div>
                  <p className="text-xs text-slate-200">
                    O código de 6 dígitos foi enviado para o WhatsApp cadastrado:{' '}
                    <strong>{maskedPhone || 'Número cadastrado'}</strong>.
                  </p>
                  <p className="text-[10px] text-slate-400">
                    Validade de 5 minutos. Limite de até 5 tentativas de validação.
                  </p>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Digite o código de 6 dígitos recebido:
                  </label>
                  <input
                    required
                    type="text"
                    maxLength={6}
                    placeholder="000000"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    className="w-full px-4 py-3 bg-[#070b0e] border border-[#182836] rounded-xl text-center text-lg font-mono text-white tracking-widest focus:border-amber-500 outline-none"
                  />
                  {otpError && (
                    <p className="text-red-400 text-[11px] mt-1">{otpError}</p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={otpLoading || otpCode.trim().length !== 6}
                  className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold transition-colors shadow-lg shadow-emerald-950/60"
                >
                  {otpLoading ? 'Validando no servidor...' : 'Validar Código & Assumir Gestão'}
                </button>
              </form>
            )}

            {/* Passo 3: Sucesso */}
            {claimStep === 'success' && (
              <div className="p-6 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
                <h3 className="text-lg font-bold text-white">Posse Confirmada com Sucesso!</h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Você agora é o administrador registrado de <strong>{business.name}</strong>. Você tem acesso imediato ao Painel da Empresa para gerenciar seu anúncio.
                </p>

                <button
                  onClick={() => {
                    setShowClaimModal(false);
                    router.push(`/painel-empresa?bizId=${business.id}`);
                  }}
                  className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-extrabold text-xs transition-colors shadow-md flex items-center justify-center gap-2 mt-2"
                >
                  Acessar Painel da Empresa Agora
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Denunciar Perfil */}
      {showReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="bg-[#0d151c] border border-red-500/30 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl relative text-xs">
            <button
              onClick={() => setShowReportModal(false)}
              className="absolute right-4 top-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              Denunciar {business.name}
            </h3>

            {reportSuccess ? (
              <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-center space-y-1">
                <Check className="w-6 h-6 mx-auto text-emerald-400" />
                <p className="font-bold">Denúncia recebida.</p>
                <p className="text-[11px] text-slate-400">Nossa equipe irá verificar os dados em até 24h.</p>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Motivo:</label>
                  <select
                    value={reportReason}
                    onChange={(e) => setReportReason(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-red-500 outline-none"
                  >
                    <option value="Violação da Carta de Princípios">Violação da Carta de Princípios / Desvio Ético</option>
                    <option value="Dados desatualizados">Telefone / Endereço incorreto</option>
                    <option value="Empresa fechada">Empresa encerrou as atividades</option>
                    <option value="Suspeita de fraude">Suspeita de golpe / Fraude</option>
                    <option value="Cobrança indevida">Propaganda enganosa / Desrespeito ao Consumidor</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Detalhes adicionais:</label>
                  <textarea
                    rows={3}
                    placeholder="Descreva o que ocorreu..."
                    value={reportDetails}
                    onChange={(e) => setReportDetails(e.target.value)}
                    className="w-full p-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-red-500 outline-none resize-none"
                  />
                </div>

                <button
                  onClick={async () => {
                    try {
                      await fetch(`/api/v1/businesses/${business.id}/report`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          reason: reportReason,
                          details: reportDetails,
                        }),
                      });
                    } catch {}
                    setReportSuccess(true);
                    setTimeout(() => {
                      setReportSuccess(false);
                      setShowReportModal(false);
                      setReportDetails('');
                    }, 2000);
                  }}
                  className="w-full py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold transition-colors shadow-md"
                >
                  Enviar Denúncia para a Curadoria Patriota Indica
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal da Carta de Princípios e Valores da Liberdade */}
      <ManifestoModal
        isOpen={showManifestoModal}
        onClose={() => setShowManifestoModal(false)}
      />

      {/* Footer */}
      <footer className="border-t border-[#182836] bg-[#070b0e] text-slate-400 text-xs py-6 mt-12">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 Patriota Indica. Rede de confiança, livre iniciativa e integridade comercial.</p>
          <div className="flex gap-4">
            <button onClick={() => setShowManifestoModal(true)} className="hover:text-amber-300">
              Carta de Princípios
            </button>
            <Link href="/" className="hover:text-amber-300">Termos de Uso</Link>
            <Link href="/" className="hover:text-amber-300">Privacidade (LGPD)</Link>
            <Link href="/painel-empresa" className="text-amber-400 hover:underline">Painel da Empresa</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
