'use client';

import React, { useState, useEffect } from 'react';
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
  FileText,
  Store,
  Navigation,
  Globe
} from 'lucide-react';
import { Suspense } from 'react';
import { INITIAL_BUSINESSES, INITIAL_CATEGORIES } from '@/lib/mockData';
import { Category } from '@/lib/types';
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
  const [categoriesList, setCategoriesList] = useState<Category[]>(INITIAL_CATEGORIES);

  useEffect(() => {
    fetch('/api/v1/categories')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setCategoriesList(data);
        }
      })
      .catch(() => {});
  }, []);

  // Mock de dados pré-preenchidos a partir do convite gerado
  const [formData, setFormData] = useState({
    responsibleName: '',
    businessName: 'Silva Instalações e Eletricista 24h',
    whatsapp: '19987654321',
    category: 'eletricista',
    custom_category: '',
    neighborhood: 'Centro',
    city: 'Campinas',
    state: 'SP',
    service_mode: 'at_customer',
    serves_at_location: true,
    serves_at_customer: true,
    serves_online: false,
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
                  {categoriesList.map((c) => (
                    <option key={c.id} value={c.slug}>
                      {c.name}
                    </option>
                  ))}
                  <option value="outra" className="font-semibold text-amber-400">
                    ➕ Outra categoria / Não encontrei meu serviço...
                  </option>
                </select>
              </div>
            </div>

            {formData.category === 'outra' && (
              <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/50 space-y-1.5">
                <label className="block text-amber-300 font-semibold text-xs flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  Qual é o seu serviço ou especialidade? *
                </label>
                <input
                  required
                  type="text"
                  placeholder="Ex: Adestrador de Cães, Psicólogo, Fisioterapeuta, Fotógrafo..."
                  value={formData.custom_category || ''}
                  onChange={(e) => setFormData({ ...formData, custom_category: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-amber-500/60 text-white placeholder-slate-500 focus:border-amber-400 outline-none text-xs"
                />
              </div>
            )}

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

            {/* Métodos de Atendimento Multi-Seleção (Checkboxes) */}
            <div className="space-y-2.5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <label className="block text-slate-300 font-semibold text-sm">
                  Métodos de Atendimento *
                </label>
                <span className="text-[11px] text-amber-400 font-medium">
                  (Marque todas as formas que você atua)
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {/* No Estabelecimento */}
                <label
                  className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                    formData.serves_at_location
                      ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                      : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={formData.serves_at_location}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        serves_at_location: e.target.checked,
                      })
                    }
                    className="mt-0.5 accent-amber-500 w-4 h-4 rounded cursor-pointer"
                  />
                  <div className="text-xs leading-tight">
                    <span className="font-semibold block text-slate-100 flex items-center gap-1">
                      <Store className="w-3.5 h-3.5 text-blue-400 inline" /> No Estabelecimento
                    </span>
                    <span className="text-[11px] text-slate-400 mt-0.5 block">
                      Balcão / loja física
                    </span>
                  </div>
                </label>

                {/* A Domicílio */}
                <label
                  className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                    formData.serves_at_customer
                      ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                      : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={formData.serves_at_customer}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        serves_at_customer: e.target.checked,
                      })
                    }
                    className="mt-0.5 accent-amber-500 w-4 h-4 rounded cursor-pointer"
                  />
                  <div className="text-xs leading-tight">
                    <span className="font-semibold block text-slate-100 flex items-center gap-1">
                      <Navigation className="w-3.5 h-3.5 text-emerald-400 inline" /> A Domicílio
                    </span>
                    <span className="text-[11px] text-slate-400 mt-0.5 block">
                      Vou até o cliente
                    </span>
                  </div>
                </label>

                {/* 100% Online */}
                <label
                  className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                    formData.serves_online
                      ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                      : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={formData.serves_online}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        serves_online: e.target.checked,
                      })
                    }
                    className="mt-0.5 accent-amber-500 w-4 h-4 rounded cursor-pointer"
                  />
                  <div className="text-xs leading-tight">
                    <span className="font-semibold block text-slate-100 flex items-center gap-1">
                      <Globe className="w-3.5 h-3.5 text-amber-400 inline" /> Online / Nacional
                    </span>
                    <span className="text-[11px] text-slate-400 mt-0.5 block">
                      Remoto / Todo o Brasil
                    </span>
                  </div>
                </label>
              </div>

              {formData.serves_at_customer && (
                <div className="p-3.5 rounded-xl bg-[#091118] border border-emerald-800/40 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <span className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                        <Navigation className="w-3.5 h-3.5 text-emerald-400" />
                        Raio Atendido a Domicílio (Máximo 150 km)
                      </span>
                      <p className="text-[11px] text-slate-400">
                        Distância máxima percorrida até o cliente a partir da sua base
                      </p>
                    </div>
                    <div className="flex items-center gap-2 self-start sm:self-auto">
                      <input
                        type="number"
                        min={1}
                        max={150}
                        value={formData.service_radius_km || ''}
                        onChange={(e) => {
                          const val = e.target.value;
                          if (val === '') {
                            setFormData({ ...formData, service_radius_km: 0 });
                            return;
                          }
                          let num = parseInt(val, 10);
                          if (isNaN(num)) num = 1;
                          if (num > 150) num = 150;
                          if (num < 1) num = 1;
                          setFormData({ ...formData, service_radius_km: num });
                        }}
                        onBlur={(e) => {
                          let num = parseInt(e.target.value, 10);
                          if (isNaN(num) || num < 1) num = 15;
                          if (num > 150) num = 150;
                          setFormData({ ...formData, service_radius_km: num });
                        }}
                        className="w-20 px-2.5 py-1.5 rounded-lg bg-[#070b0e] border border-[#182836] text-white focus:border-emerald-500 outline-none text-sm text-center font-bold"
                      />
                      <span className="text-xs text-slate-300 font-medium">km</span>
                    </div>
                  </div>

                  {/* Slider de Alcance */}
                  <div className="space-y-1">
                    <input
                      type="range"
                      min={1}
                      max={150}
                      step={1}
                      value={formData.service_radius_km || 20}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          service_radius_km: Number(e.target.value),
                        })
                      }
                      className="w-full accent-emerald-500 cursor-pointer h-1.5 bg-[#070b0e] rounded-lg"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>1 km (Local)</span>
                      <span>75 km (Regional)</span>
                      <span>150 km (Máximo)</span>
                    </div>
                  </div>

                  {/* Botões Rápidos de Preset */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-[10px] text-slate-400 mr-1">Atalhos:</span>
                    {[10, 25, 50, 100, 150].map((km) => (
                      <button
                        key={`preset-${km}`}
                        type="button"
                        onClick={() => setFormData({ ...formData, service_radius_km: km })}
                        className={`px-2 py-0.5 rounded-md text-[11px] font-semibold transition-all border ${
                          formData.service_radius_km === km
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                            : 'bg-[#070b0e] text-slate-400 border-[#182836] hover:text-white'
                        }`}
                      >
                        {km} km
                      </button>
                    ))}
                  </div>

                  {formData.service_radius_km >= 150 && (
                    <p className="text-[11px] text-amber-300/90 bg-amber-950/20 p-2 rounded-lg border border-amber-500/20">
                      💡 150 km é o limite regional padrão para deslocamento. Para clientes em outros estados ou remotos, marque também a opção <strong>Online / Nacional</strong>.
                    </p>
                  )}
                </div>
              )}
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
