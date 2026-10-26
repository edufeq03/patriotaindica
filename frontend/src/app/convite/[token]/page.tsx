'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { 
  ShieldCheck, 
  CheckCircle2, 
  Send, 
  Sparkles, 
  Building2, 
  MapPin, 
  Phone, 
  Clock, 
  ArrowLeft,
  Star,
  Award,
  ArrowRight,
  FileText
} from 'lucide-react';
import { Suspense } from 'react';
import { INITIAL_BUSINESSES, INITIAL_CATEGORIES } from '@/lib/mockData';
import ManifestoModal, { MANIFESTO_VERSION } from '@/components/ManifestoModal';

export default function InvitationPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#070b0e] text-slate-400 p-8 text-center text-xs">Carregando convite...</div>}>
      <InvitationContent />
    </Suspense>
  );
}

function InvitationContent() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [showManifestoModal, setShowManifestoModal] = useState(false);

  // Mock de dados pré-preenchidos a partir do convite gerado
  const [formData, setFormData] = useState({
    responsibleName: '',
    businessName: 'Silva Instalações e Eletricista 24h',
    whatsapp: '19987654321',
    category: 'eletricista',
    neighborhood: 'Centro',
    city: 'Campinas',
    state: 'SP',
    service_mode: 'at_customer',
    service_radius_km: 25,
    description: 'Especialista em reformas elétricas, quadros de distribuição e laudos técnicos.',
    instagram: 'silvaeletrica_campinas',
    website: 'https://silvaeletrica.com.br',
    accepted_manifesto: true,
  });

  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col font-sans selection:bg-amber-500 selection:text-black">
      {/* Top Navbar */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-xs font-semibold text-slate-300 hover:text-amber-300 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Página Inicial
          </Link>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs px-3 py-1 rounded-full bg-amber-950/80 text-amber-300 border border-amber-500/40 shadow-sm font-semibold">
              <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
              Convite Exclusivo Patriota Indica
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-2xl mx-auto px-4 py-10 flex-1 w-full space-y-6">
        {/* Banner VIP Dourado */}
        <div className="p-6 rounded-2xl bg-gradient-to-br from-[#0d151c] via-[#121e29] to-[#070b0e] border border-amber-500/40 shadow-2xl space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-2xl pointer-events-none" />
          
          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs uppercase tracking-wider">
            <Award className="w-4 h-4" />
            <span>Convite Exclusivo para Lojistas e Prestadores</span>
          </div>

          <h1 className="text-2xl md:text-3xl font-black text-white leading-tight">
            Sua empresa foi pré-selecionada para a rede Patriota Indica!
          </h1>

          <p className="text-xs text-slate-300 leading-relaxed">
            Nossa equipe de curadoria identificou seu negócio como referência na região. Confira abaixo os dados
            pré-cadastrados, complemente com suas especialidades e ative seu perfil gratuito.
          </p>
        </div>

        {isSubmitted ? (
          <div className="p-8 rounded-2xl bg-[#0d151c] border border-emerald-500/50 text-center space-y-4 shadow-2xl">
            <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto" />
            <h2 className="text-2xl font-black text-white">Cadastro Enviado com Sucesso!</h2>
            <p className="text-xs text-slate-300 max-w-md mx-auto leading-relaxed">
              Recebemos suas informações com o token de convite <code className="text-amber-400 font-mono">{token || 'conv_campinas'}</code>. 
              Nossa equipe fará a liberação em até 24 horas úteis.
            </p>
            <div className="pt-2">
              <Link
                href="/painel-empresa"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-extrabold text-xs transition-colors shadow-lg"
              >
                Conhecer o Painel da Empresa
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 md:p-8 rounded-2xl bg-[#0d151c] border border-[#182836] space-y-5 text-xs shadow-xl">
            <h2 className="text-base font-bold text-white flex items-center gap-2 pb-2 border-b border-[#182836]">
              <Building2 className="w-4 h-4 text-emerald-400" />
              Confirmação de Dados da Empresa
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Nome do Negócio / Fantasia *</label>
                <input
                  required
                  type="text"
                  value={formData.businessName}
                  onChange={(e) => setFormData({ ...formData, businessName: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none font-medium"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Nome do Responsável *</label>
                <input
                  required
                  type="text"
                  placeholder="Seu nome completo"
                  value={formData.responsibleName}
                  onChange={(e) => setFormData({ ...formData, responsibleName: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">WhatsApp de Atendimento *</label>
                <input
                  required
                  type="text"
                  value={formData.whatsapp}
                  onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Categoria Principal *</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                >
                  {INITIAL_CATEGORIES.map((c) => (
                    <option key={c.id} value={c.slug}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Bairro / Região *</label>
                <input
                  required
                  type="text"
                  value={formData.neighborhood}
                  onChange={(e) => setFormData({ ...formData, neighborhood: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Cidade / UF *</label>
                <input
                  disabled
                  type="text"
                  value={`${formData.city} - ${formData.state}`}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e]/50 border border-[#182836] text-slate-400 font-medium cursor-not-allowed"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Modo de Atendimento</label>
                <select
                  value={formData.service_mode}
                  onChange={(e) => setFormData({ ...formData, service_mode: e.target.value })}
                  className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                >
                  <option value="at_customer">A domicílio (vou até o cliente)</option>
                  <option value="at_location">No meu estabelecimento</option>
                  <option value="both">Ambos</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Raio de Atendimento (km)</label>
                <input
                  type="number"
                  value={formData.service_radius_km}
                  onChange={(e) => setFormData({ ...formData, service_radius_km: Number(e.target.value) })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">Descrição e Diferenciais *</label>
              <textarea
                required
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none resize-none leading-relaxed"
              />
            </div>

            {/* Adesão à Carta de Princípios e Valores (Blindagem Jurídica) */}
            <div className="p-4 rounded-xl bg-amber-950/25 border border-amber-500/40 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                  <Award className="w-4 h-4 text-amber-400" />
                  Carta de Princípios e Valores da Liberdade *
                </span>
                <button
                  type="button"
                  onClick={() => setShowManifestoModal(true)}
                  className="text-[11px] text-amber-300 hover:text-white underline font-semibold flex items-center gap-1"
                >
                  <FileText className="w-3 h-3" />
                  Ler Carta Completa
                </button>
              </div>
              <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  required
                  checked={formData.accepted_manifesto}
                  onChange={(e) => setFormData({ ...formData, accepted_manifesto: e.target.checked })}
                  className="mt-0.5 rounded border-gray-700 text-amber-500 focus:ring-amber-500 bg-[#070b0e]"
                />
                <span>
                  Declaro que li e subscrevo voluntariamente a <strong>Carta de Princípios da Liberdade</strong> (livre iniciativa, defesa irrestrita da propriedade privada, ética cristã/ocidental e respeito integral ao consumidor).
                </span>
              </label>
            </div>

            <button
              type="submit"
              className="w-full py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-sm transition-colors shadow-lg shadow-emerald-950/60 border border-amber-400/40 flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="w-5 h-5 text-amber-300" />
              Subscrever a Carta & Ativar Perfil Oficial
            </button>
          </form>
        )}
      </main>

      {/* Modal da Carta de Princípios e Valores */}
      <ManifestoModal
        isOpen={showManifestoModal}
        onClose={() => setShowManifestoModal(false)}
        showAcceptButton={!formData.accepted_manifesto}
        onAccept={() => setFormData((prev) => ({ ...prev, accepted_manifesto: true }))}
      />
    </div>
  );
}
