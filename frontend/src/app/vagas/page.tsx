'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import {
  Briefcase,
  Search,
  MapPin,
  Building2,
  Clock,
  ShieldCheck,
  Send,
  AlertTriangle,
  Loader2,
  ArrowLeft,
  Filter,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  Store,
} from 'lucide-react';
import { BrasilLogo } from '@/components/BrasilLogo';
import ReportJobModal from '@/components/ReportJobModal';

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

const CONTRACT_TYPE_OPTIONS = [
  { value: 'all', label: 'Todos os Contratos' },
  { value: 'clt', label: 'CLT (Efetivo)' },
  { value: 'temporario', label: 'Temporário' },
  { value: 'meio_periodo', label: 'Meio Período' },
  { value: 'estagio', label: 'Estágio' },
  { value: 'aprendiz', label: 'Jovem Aprendiz' },
  { value: 'autonomo', label: 'Autônomo / PJ' },
];

const CONTRACT_TYPE_MAP: Record<string, string> = {
  clt: 'FULL_TIME',
  temporario: 'TEMPORARY',
  meio_periodo: 'PART_TIME',
  estagio: 'INTERN',
  aprendiz: 'OTHER',
  autonomo: 'CONTRACTOR',
};

// Escapa seguro para JSON-LD XSS prevention (Seção 8 e 13)
function escapeJsonLd(str: string): string {
  return str.replace(/</g, '\\u003c').replace(/>/g, '\\u003e');
}

export default function VagasPublicPage() {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtros
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [selectedContract, setSelectedContract] = useState('all');

  // Modal de Denúncia
  const [reportJob, setReportJob] = useState<{ id: string; title: string; businessName: string } | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetch('/api/v1/jobs?limit=100')
      .then((res) => {
        if (!res.ok) throw new Error('Não foi possível carregar as vagas disponíveis.');
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setJobs(Array.isArray(data.results) ? data.results : []);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Erro ao carregar vagas.');
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Cidades únicas disponíveis
  const citiesList = useMemo(() => {
    const set = new Set<string>();
    jobs.forEach((j) => {
      if (j.business?.city) set.add(j.business.city);
    });
    return Array.from(set).sort();
  }, [jobs]);

  // Vagas Filtradas
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      if (selectedContract !== 'all' && job.contract_type !== selectedContract) {
        return false;
      }
      if (selectedCity && job.business?.city?.toLowerCase() !== selectedCity.toLowerCase()) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchTitle = job.title.toLowerCase().includes(q);
        const matchDesc = job.description?.toLowerCase().includes(q);
        const matchBiz = job.business?.name.toLowerCase().includes(q);
        const matchNeigh = job.business?.neighborhood.toLowerCase().includes(q);
        if (!matchTitle && !matchDesc && !matchBiz && !matchNeigh) {
          return false;
        }
      }
      return true;
    });
  }, [jobs, searchQuery, selectedCity, selectedContract]);

  // Geração do JSON-LD JobPosting estruturado (Google Jobs)
  // SOMENTE para vagas com descrição >= 40 caracteres (Seção 8)
  const jsonLdData = useMemo(() => {
    const validJobs = filteredJobs.filter(
      (j) => j.description && j.description.trim().length >= 40
    );
    if (validJobs.length === 0) return null;

    const schemaItems = validJobs.map((j) => ({
      '@context': 'https://schema.org',
      '@type': 'JobPosting',
      title: j.title,
      description: j.description || j.title,
      datePosted: j.published_at || new Date().toISOString(),
      validThrough: j.expires_at || undefined,
      employmentType: CONTRACT_TYPE_MAP[j.contract_type] || 'FULL_TIME',
      hiringOrganization: {
        '@type': 'Organization',
        name: j.business.name,
        sameAs: `https://patriotaindica.com.br`,
      },
      jobLocation: {
        '@type': 'Place',
        address: {
          '@type': 'PostalAddress',
          addressLocality: j.business.city,
          addressRegion: 'BR',
          addressCountry: 'BR',
        },
      },
    }));

    return escapeJsonLd(JSON.stringify(schemaItems));
  }, [filteredJobs]);

  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-200 flex flex-col">
      {/* Schema.org JSON-LD para SEO no Google Jobs */}
      {jsonLdData && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLdData }}
        />
      )}

      {/* Top Header */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 sticky top-0 z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Vitrine Comercial</span>
            </Link>
            <div className="h-5 w-[1px] bg-[#182836]" />
            <div className="flex items-center gap-2">
              <BrasilLogo size={28} className="w-7 h-7 !rounded-lg" />
              <span className="font-extrabold text-white text-sm sm:text-base tracking-tight flex items-center gap-2">
                Patriota Indica
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  Vagas de Emprego
                </span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              href="/painel-empresa"
              className="px-3.5 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <Store className="w-3.5 h-3.5" />
              <span>Anunciar Vaga da Minha Empresa</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero & Banner de Confiança */}
      <section className="bg-gradient-to-b from-[#0d151c] to-[#070b0e] border-b border-[#182836] py-10 px-4">
        <div className="max-w-4xl mx-auto text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-bold">
            <Briefcase className="w-3.5 h-3.5 text-amber-400" />
            <span>Oportunidades em Empresas de Confiança</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-black text-white tracking-tight">
            Vagas de Trabalho da Livre Iniciativa
          </h1>

          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Conectamos profissionais de bem diretamente ao WhatsApp oficial de empresas recomendadas, sem burocracia, taxas ou intermediários.
          </p>

          {/* Aviso Anti-Golpe */}
          <div className="p-3.5 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-[#0d151c] to-amber-950/40 border border-emerald-500/40 text-emerald-300 text-xs flex items-center justify-center gap-3 shadow-lg max-w-2xl mx-auto text-left">
            <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0" />
            <span className="text-[11px] leading-relaxed">
              <strong>Proteção ao Trabalhador:</strong> Nenhuma empresa séria cobra taxa de inscrição, compra de kits ou cursos para contratar. Se cobrarem qualquer valor, denuncie imediatamente.
            </span>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 flex-1 w-full space-y-6">
        {/* Barra de Filtros */}
        <div className="p-4 rounded-2xl bg-[#0d151c] border border-[#182836] shadow-xl flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="relative w-full md:w-1/3">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por cargo, função ou empresa..."
              className="w-full pl-10 pr-4 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white placeholder-slate-500 focus:border-amber-500 outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            {/* Filtro Cidade */}
            {citiesList.length > 0 && (
              <select
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
              >
                <option value="">Todas as Cidades ({citiesList.length})</option>
                {citiesList.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            )}

            {/* Filtro Tipo de Contrato */}
            <select
              value={selectedContract}
              onChange={(e) => setSelectedContract(e.target.value)}
              className="px-3 py-2 bg-[#070b0e] border border-[#182836] rounded-xl text-xs text-white focus:border-amber-500 outline-none"
            >
              {CONTRACT_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            {(searchQuery || selectedCity || selectedContract !== 'all') && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCity('');
                  setSelectedContract('all');
                }}
                className="px-3 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition-colors"
              >
                Limpar filtros
              </button>
            )}
          </div>
        </div>

        {/* Resumo da busca */}
        <div className="flex items-center justify-between text-xs text-slate-400 px-1">
          <span>
            Exibindo <strong>{filteredJobs.length}</strong> {filteredJobs.length === 1 ? 'vaga aberta' : 'vagas abertas'}
          </span>
          <span className="text-slate-500">
            Atualizado em tempo real com empresas verificadas
          </span>
        </div>

        {/* Grid de Vagas */}
        {loading ? (
          <div className="py-20 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
            <span className="text-xs">Consultando vagas abertas...</span>
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs text-center space-y-2">
            <AlertTriangle className="w-8 h-8 text-red-400 mx-auto" />
            <p className="font-semibold">{error}</p>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="py-16 text-center space-y-4 rounded-3xl bg-[#0d151c] border border-[#182836] p-8">
            <Briefcase className="w-12 h-12 text-slate-600 mx-auto" />
            <h3 className="text-base font-bold text-white">Nenhuma vaga encontrada com esses filtros</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Tente selecionar outra cidade ou limpar o termo de busca. Você também pode convidar empresas e comércios da sua região para publicarem vagas gratuitas na plataforma.
            </p>
            <div className="pt-2">
              <Link
                href="/painel-empresa"
                className="px-4 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold inline-flex items-center gap-1.5"
              >
                <Store className="w-3.5 h-3.5" />
                Sou Lojista e Quero Anunciar Vagas
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredJobs.map((job) => (
              <div
                key={job.id}
                className="rounded-2xl bg-[#0d151c] border border-[#182836] hover:border-amber-500/40 transition-all duration-300 p-5 flex flex-col justify-between shadow-xl hover:shadow-2xl space-y-4 group"
              >
                <div className="space-y-3">
                  {/* Topo do Card: Empresa e Localização */}
                  <div className="flex items-center gap-3 pb-3 border-b border-[#182836]">
                    <div className="w-11 h-11 rounded-xl bg-[#070b0e] border border-[#182836] flex items-center justify-center overflow-hidden shrink-0">
                      {job.business.logo_url ? (
                        <img
                          src={job.business.logo_url}
                          alt={job.business.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Building2 className="w-5 h-5 text-amber-400" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <span className="text-[11px] font-semibold text-slate-400 block truncate">
                        {job.business.name}
                      </span>
                      <p className="text-[11px] text-slate-500 flex items-center gap-1 truncate">
                        <MapPin className="w-3 h-3 text-amber-400 shrink-0" />
                        {job.business.neighborhood}, {job.business.city}
                      </p>
                    </div>
                  </div>

                  {/* Informações da Vaga */}
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-[#182836] text-amber-300 uppercase">
                        {job.contract_type}
                      </span>
                      {job.openings_count > 1 && (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/20">
                          {job.openings_count} vagas
                        </span>
                      )}
                    </div>

                    <h2 className="text-base font-bold text-white group-hover:text-amber-400 transition-colors line-clamp-2">
                      {job.title}
                    </h2>

                    {job.published_at && (
                      <p className="text-[11px] text-slate-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Publicada em {new Date(job.published_at).toLocaleDateString('pt-BR')}
                      </p>
                    )}
                  </div>

                  {/* Descrição */}
                  {job.description && (
                    <p className="text-xs text-slate-300 bg-[#070b0e] p-3 rounded-xl border border-[#182836]/60 line-clamp-4 leading-relaxed">
                      {job.description}
                    </p>
                  )}
                </div>

                {/* Footer do Card com CTA e Denúncia */}
                <div className="space-y-2 pt-2 border-t border-[#182836]/50">
                  <a
                    href={`/go/job/${job.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs md:text-sm shadow-md shadow-emerald-950/60 transition-all border border-emerald-400/30"
                  >
                    <Send className="w-4 h-4" />
                    <span>Quero me candidatar via WhatsApp</span>
                  </a>

                  <div className="flex items-center justify-between text-[11px] px-1 text-slate-500">
                    <span>Sem intermediários</span>
                    <button
                      type="button"
                      onClick={() =>
                        setReportJob({
                          id: job.id,
                          title: job.title,
                          businessName: job.business.name,
                        })
                      }
                      className="hover:text-red-400 transition-colors underline"
                    >
                      Denunciar vaga
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Modal de Denúncia */}
      {reportJob && (
        <ReportJobModal
          jobId={reportJob.id}
          jobTitle={reportJob.title}
          businessName={reportJob.businessName}
          isOpen={true}
          onClose={() => setReportJob(null)}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-[#182836] bg-[#070b0e] text-slate-400 text-xs py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <BrasilLogo size={20} className="w-5 h-5 !rounded-md" />
            <span>© 2026 Patriota Indica • Vagas e Oportunidades da Livre Iniciativa.</span>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <Link href="/" className="hover:text-amber-300">Vitrine Principal</Link>
            <Link href="/termos" className="hover:text-amber-300">Termos de Uso</Link>
            <Link href="/privacidade" className="hover:text-amber-300">Privacidade (LGPD)</Link>
            <Link href="/painel-empresa" className="text-amber-400 font-semibold hover:underline">
              Painel da Empresa
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
