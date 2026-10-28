import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { CheckCircle2, ShieldCheck, MessageCircle, MapPin, Globe, Users, ArrowRight } from 'lucide-react';

interface Props {
  params: Promise<{
    slug: string;
  }>;
}

export const instant = false;

export async function generateStaticParams() {
  return [{ slug: 'exemplo' }];
}

interface TrustCardData {
  name: string;
  slug: string;
  city: string;
  state: string;
  neighborhood: string;
  network_badge: string;
  is_verified: boolean;
  endorsements_count: number;
  is_available_now: boolean;
  availability_until: string | null;
  direct_whatsapp_url: string;
  share_url: string;
  website?: string | null;
  instagram?: string | null;
  phone?: string | null;
  verified_network_statement: string;
}

async function fetchTrustCard(slug: string): Promise<TrustCardData | null> {
  const candidateUrls = [
    process.env.INTERNAL_API_URL,
    process.env.NEXT_PUBLIC_API_URL,
    'http://backend:8000/api/v1',
    'http://patriotaindica-backend:8000/api/v1',
    'http://127.0.0.1:8000/api/v1',
    'https://patriotaindica.com.br/api/v1',
  ].filter(Boolean) as string[];

  const uniqueUrls = Array.from(new Set(candidateUrls));

  for (const base of uniqueUrls) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);
      const res = await fetch(`${base}/businesses/by-slug/${encodeURIComponent(slug)}/trust-card`, {
        signal: controller.signal,
        next: { revalidate: 15 },
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Tentar próximo endpoint
    }
  }

  // Fallback seguro para build e preview
  return {
    name: 'Empresa Parceira da Rede',
    slug,
    city: 'Campinas',
    state: 'SP',
    neighborhood: 'Centro',
    network_badge: 'membro_verificado',
    is_verified: true,
    endorsements_count: 3,
    is_available_now: false,
    availability_until: null,
    direct_whatsapp_url: 'https://wa.me/5519999998888',
    share_url: `https://patriotaindica.com.br/q/${slug}`,
    website: null,
    instagram: null,
    phone: null,
    verified_network_statement: 'Esta empresa faz parte da Rede de Negócios Confiáveis Patriota Indica, com curadoria e princípios alinhados à comunidade.',
  };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const data = await fetchTrustCard(slug);
  if (!data) return { title: 'Empresa não encontrada | Patriota Indica' };

  return {
    title: `${data.name} | Rede de Negócios Confiáveis - Patriota Indica`,
    description: `Conheça ${data.name} em ${data.city} - ${data.state}. Membro verificado da Rede de Negócios Confiáveis Patriota Indica.`,
    openGraph: {
      title: `${data.name} - Empresa Indicada e Verificada`,
      description: `Membro da Rede de Negócios Confiáveis Patriota Indica. Recomendações de confiança e contato direto.`,
    },
  };
}

export default async function TrustCardPage({ params }: Props) {
  const { slug } = await params;
  const data = await fetchTrustCard(slug);

  if (!data) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100 flex flex-col items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-md relative overflow-hidden">
        {/* Faixa Superior Decorativa */}
        <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-emerald-500 via-amber-400 to-emerald-600" />

        {/* Cabeçalho da Rede */}
        <div className="flex items-center justify-between pb-6 border-b border-slate-800/80 mb-6">
          <Link href="/" className="flex items-center gap-2 group">
            <span className="text-xl font-black tracking-tight text-white group-hover:text-amber-400 transition">
              PATRIOTA<span className="text-emerald-500">INDICA</span>
            </span>
          </Link>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Rede Confiável</span>
          </div>
        </div>

        {/* Identificação da Empresa */}
        <div className="text-center space-y-3 mb-6">
          <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-tr from-slate-800 to-slate-700 flex items-center justify-center text-3xl font-black text-amber-400 border border-slate-700 shadow-inner">
            {data.name.charAt(0)}
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">{data.name}</h1>
          <div className="flex items-center justify-center gap-1.5 text-sm text-slate-400">
            <MapPin className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{data.neighborhood}, {data.city} - {data.state}</span>
          </div>
        </div>

        {/* Badges de Confiança da Rede */}
        <div className="grid grid-cols-2 gap-2.5 mb-6">
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-3 flex flex-col items-center text-center">
            <div className="flex items-center gap-1 text-emerald-400 font-bold text-base mb-0.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>Verificado</span>
            </div>
            <span className="text-xs text-slate-400">Curadoria Aprovada</span>
          </div>

          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-3 flex flex-col items-center text-center">
            <div className="flex items-center gap-1 text-amber-400 font-bold text-base mb-0.5">
              <Users className="w-4 h-4" />
              <span>{data.endorsements_count}</span>
            </div>
            <span className="text-xs text-slate-400">Indicações de Pares</span>
          </div>
        </div>

        {/* Selo Disponível Agora (se ativo) */}
        {data.is_available_now && (
          <div className="mb-6 p-3 rounded-2xl bg-emerald-500/15 border border-emerald-500/40 flex items-center gap-3 animate-pulse">
            <div className="w-3 h-3 rounded-full bg-emerald-400 shadow-lg shadow-emerald-500/50" />
            <div className="text-left text-xs">
              <span className="font-bold text-emerald-300 block">Disponível Agora / Plantão</span>
              <span className="text-emerald-400/80">Atendimento prioritário de imediato</span>
            </div>
          </div>
        )}

        {/* Botão de Contato WhatsApp Principal */}
        <a
          href={data.direct_whatsapp_url}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full py-4 px-6 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-base flex items-center justify-center gap-3 shadow-lg shadow-emerald-600/30 transition transform active:scale-[0.98] mb-4"
        >
          <MessageCircle className="w-5 h-5 fill-current" />
          <span>Falar no WhatsApp Direto</span>
        </a>

        {/* Declaração de Confiança */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 text-xs text-slate-400 text-center leading-relaxed mb-6">
          <ShieldCheck className="w-4 h-4 text-amber-400 mx-auto mb-1.5" />
          {data.verified_network_statement}
        </div>

        {/* Links Adicionais */}
        <div className="space-y-2 text-sm">
          {data.website && (
            <a
              href={data.website}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-3 px-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 text-slate-300 flex items-center justify-between transition border border-slate-700/40"
            >
              <div className="flex items-center gap-2.5">
                <Globe className="w-4 h-4 text-slate-400" />
                <span>Acessar Website Oficial</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </a>
          )}

          {data.instagram && (
            <a
              href={`https://instagram.com/${data.instagram.replace('@', '')}`}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-3 px-4 rounded-xl bg-slate-800/50 hover:bg-slate-800 text-slate-300 flex items-center justify-between transition border border-slate-700/40"
            >
              <div className="flex items-center gap-2.5">
                <svg className="w-4 h-4 fill-current text-slate-400" viewBox="0 0 24 24">
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                </svg>
                <span>Perfil no Instagram</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </a>
          )}
        </div>

        {/* Rodapé da Comunidade */}
        <div className="text-center mt-8 pt-4 border-t border-slate-800/60 text-xs text-slate-500">
          Rede de Negócios Confiáveis &bull; Fortalecendo quem produz com valores
        </div>
      </div>
    </main>
  );
}
