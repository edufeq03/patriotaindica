'use client';

import React, { useState, useMemo, useRef, useEffect } from 'react';
import Link from 'next/link';
import { BrasilLogo } from '@/components/BrasilLogo';
import { 
  Search, 
  MapPin, 
  ShieldCheck, 
  CheckCircle2, 
  MessageCircle, 
  Navigation, 
  Sparkles, 
  Zap, 
  Wind, 
  Droplets, 
  Key, 
  Cake, 
  Utensils, 
  Car, 
  Hammer, 
  PawPrint, 
  Flower2, 
  Building2, 
  SlidersHorizontal, 
  PlusCircle, 
  X, 
  Clock, 
  ArrowRight, 
  Shield, 
  Star, 
  Award, 
  Store, 
  FileText,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { INITIAL_BUSINESSES, INITIAL_CATEGORIES, calculateDistanceKm } from '@/lib/mockData';
import { Business, Category, ListingType } from '@/lib/types';
import ManifestoModal, { MANIFESTO_VERSION } from '@/components/ManifestoModal';

// Mapeamento de ícones para as categorias
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  zap: <Zap className="w-4 h-4 text-amber-400" />,
  wind: <Wind className="w-4 h-4 text-blue-400" />,
  droplets: <Droplets className="w-4 h-4 text-blue-400" />,
  key: <Key className="w-4 h-4 text-amber-400" />,
  cake: <Cake className="w-4 h-4 text-amber-400" />,
  utensils: <Utensils className="w-4 h-4 text-amber-400" />,
  car: <Car className="w-4 h-4 text-blue-400" />,
  hammer: <Hammer className="w-4 h-4 text-amber-400" />,
  'paw-print': <PawPrint className="w-4 h-4 text-emerald-400" />,
  'flower-2': <Flower2 className="w-4 h-4 text-emerald-400" />,
  sparkles: <Sparkles className="w-4 h-4 text-amber-400" />,
};

const BRAZIL_STATES = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
];

function formatWhatsAppUrl(whatsapp?: string, name?: string): string {
  if (!whatsapp) return '#';
  const clean = whatsapp.replace(/\D/g, '');
  const withDdi = clean.startsWith('55') ? clean : `55${clean}`;
  const text = encodeURIComponent(`Olá! Vi seu anúncio no Patriota Indica e gostaria de solicitar informações/orçamento sobre ${name || 'seus serviços'}.`);
  return `https://wa.me/${withDdi}?text=${text}`;
}

export default function HomePage() {
  // Estado de localização (Default: Centro de Campinas - SP)
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number; label: string }>({
    lat: -22.9056,
    lng: -47.0608,
    label: 'Campinas - SP',
  });
  const [isLocating, setIsLocating] = useState(false);
  const [locationSuccess, setLocationSuccess] = useState(false);

  // Filtros de busca
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<ListingType | 'all'>('all');
  const [maxDistanceKm, setMaxDistanceKm] = useState<number | null>(null);

  // Ref e função para rolagem horizontal das categorias
  const categoriesRef = useRef<HTMLDivElement>(null);
  const scrollCategories = (direction: 'left' | 'right') => {
    if (categoriesRef.current) {
      const scrollAmount = direction === 'left' ? -280 : 280;
      categoriesRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
  };

  // Categorias dinâmicas sincronizadas com o Admin
  const [categoriesList, setCategoriesList] = useState<Category[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('guia_local_categories');
      if (saved) {
        try { return JSON.parse(saved); } catch (e) {}
      }
    }
    return INITIAL_CATEGORIES;
  });

  // Lista local de empresas
  const [businesses, setBusinesses] = useState<Business[]>(INITIAL_BUSINESSES);

  // Modais
  const [showApplicationModal, setShowApplicationModal] = useState(false);
  const [showManifestoModal, setShowManifestoModal] = useState(false);

  // Form State para Candidatura (Canal C)
  const [applicationForm, setApplicationForm] = useState({
    name: '',
    category_slug: 'eletricista',
    document_number: '',
    whatsapp: '',
    neighborhood: '',
    city: '',
    state: 'SP',
    service_mode: 'at_customer' as 'at_customer' | 'at_location' | 'both' | 'online',
    service_radius_km: 20,
    description: '',
    accepted_manifesto: false,
    accepted_privacy: false,
  });
  const [applicationSubmitted, setApplicationSubmitted] = useState(false);
  const [applicationSubmitting, setApplicationSubmitting] = useState(false);
  const [applicationErrorMsg, setApplicationErrorMsg] = useState<string | null>(null);

  // Sincronização inicial com o Backend (Categorias e Empresas da Base)
  useEffect(() => {
    let isMounted = true;
    async function syncData() {
      try {
        const catRes = await fetch('/api/v1/categories');
        if (catRes.ok) {
          const data = await catRes.json();
          if (isMounted && Array.isArray(data) && data.length > 0) {
            setCategoriesList(data);
          }
        }
      } catch (err) {
        console.warn('Usando categorias locais:', err);
      }

      try {
        const searchRes = await fetch('/api/v1/search?page=1&limit=50');
        if (searchRes.ok) {
          const data = await searchRes.json();
          if (isMounted && data?.results && Array.isArray(data.results) && data.results.length > 0) {
            setBusinesses(data.results.map((b: any) => ({
              ...b,
              status: b.status || 'approved',
              category_name: b.category_name || 'Serviços',
              category_slug: b.category_slug || (b.category_name ? b.category_name.toLowerCase().replace(/\s+/g, '-') : 'servicos'),
              whatsapp: b.whatsapp || '',
              latitude: typeof b.latitude === 'number' ? b.latitude : -22.9064,
              longitude: typeof b.longitude === 'number' ? b.longitude : -47.0592,
              distance_km: typeof b.distance_km === 'number' ? b.distance_km : 0,
            })));
          }
        }
      } catch (err) {
        console.warn('Usando catálogo local:', err);
      }
    }
    syncData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Obter localização do GPS do usuário
  const handleGetLocation = () => {
    setIsLocating(true);
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            label: 'Sua localização atual (GPS)',
          });
          setIsLocating(false);
          setLocationSuccess(true);
        },
        (error) => {
          console.warn('Geolocalização não permitida:', error);
          setIsLocating(false);
          alert('Não foi possível obter sua localização exata. Mantendo busca em Campinas - SP.');
        },
        { timeout: 10000 }
      );
    } else {
      setIsLocating(false);
      alert('Geolocalização não suportada pelo navegador.');
    }
  };

  // Filtragem e ordenação por proximidade
  const filteredBusinesses = useMemo(() => {
    return businesses
      .filter((b) => {
        // Regra Inegociável 1: Apenas empresas APROVADAS aparecem na busca pública
        if (b.status && b.status !== 'approved') return false;

        // Filtro por tipo (serviço / produto)
        if (selectedType !== 'all' && b.listing_type !== selectedType && b.listing_type !== 'both') {
          return false;
        }

        // Filtro por categoria
        if (selectedCategory && b.category_slug !== selectedCategory) {
          return false;
        }

        // Filtro por busca textual (sem acento e case insensitive)
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          const matchName = b.name.toLowerCase().includes(q);
          const matchDesc = b.description?.toLowerCase().includes(q);
          const matchCat = b.category_name?.toLowerCase().includes(q);
          const matchNeigh = b.neighborhood?.toLowerCase().includes(q);
          if (!matchName && !matchDesc && !matchCat && !matchNeigh) {
            return false;
          }
        }

        // Se for modalidade 100% online ou se não houver filtro de raio (padrão Brasil), exibe
        if (b.service_mode === 'online' || maxDistanceKm === null) return true;

        // Se o usuário digitou uma busca textual, não restringe por raio físico
        if (searchQuery.trim()) return true;

        // Cálculo de distância física segura
        const hasCoords = typeof b.latitude === 'number' && typeof b.longitude === 'number';
        const dist = typeof b.distance_km === 'number'
          ? b.distance_km
          : (hasCoords ? calculateDistanceKm(userLocation.lat, userLocation.lng, b.latitude!, b.longitude!) : 0);

        // Regra Inegociável 6: Empresas cujo raio cobre o usuário OU estão no raio máximo
        if (b.service_mode === 'at_customer' || b.service_mode === 'both') {
          const radius = b.service_radius_km || 20;
          return dist <= radius || dist <= maxDistanceKm;
        }

        return dist <= maxDistanceKm;
      })
      .map((b) => {
        const hasCoords = typeof b.latitude === 'number' && typeof b.longitude === 'number';
        const dist = typeof b.distance_km === 'number'
          ? b.distance_km
          : (hasCoords ? calculateDistanceKm(userLocation.lat, userLocation.lng, b.latitude!, b.longitude!) : 0);
        return {
          ...b,
          distance_km: dist,
        };
      })
      .sort((a, b) => (a.distance_km || 0) - (b.distance_km || 0));
  }, [businesses, userLocation, searchQuery, selectedCategory, selectedType, maxDistanceKm]);

  // Submeter Candidatura Real (Canal C - "Quero ser indicado" -> PostgreSQL)
  const handleSubmitApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    setApplicationSubmitting(true);
    setApplicationErrorMsg(null);

    const cat = categoriesList.find((c) => c.slug === applicationForm.category_slug);
    const isUuid = cat?.id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(cat.id);

    // Limpar documento: se vazio, envia null para não disparar validação de checksum
    const rawDoc = applicationForm.document_number?.trim();
    const cleanDoc = rawDoc ? rawDoc.replace(/\D/g, '') : null;
    const docType = cleanDoc && cleanDoc.length === 11 ? 'CPF' : 'CNPJ';

    const payload = {
      name: applicationForm.name.trim(),
      description: applicationForm.description.trim() || null,
      listing_type: 'service',
      document_type: cleanDoc ? docType : 'CNPJ',
      document_number: cleanDoc || null,
      whatsapp: applicationForm.whatsapp.trim(),
      neighborhood: applicationForm.neighborhood.trim(),
      city: applicationForm.city.trim() || 'Campinas',
      state: (applicationForm.state.trim() || 'SP').toUpperCase(),
      service_mode: applicationForm.service_mode,
      service_radius_km: applicationForm.service_radius_km || 20,
      category_ids: isUuid && cat ? [cat.id] : [],
      primary_category_id: isUuid && cat ? cat.id : null,
      proposed_niche: (!isUuid && cat) ? cat.name : null,
      show_full_address: false,
    };

    try {
      const res = await fetch('/api/v1/businesses/application', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        let msg = 'Erro ao cadastrar empresa. Verifique os dados informados.';
        if (data?.detail) {
          if (typeof data.detail === 'string') {
            msg = data.detail;
          } else if (Array.isArray(data.detail)) {
            msg = data.detail.map((err: any) => err.msg || err.message).join(' | ');
          }
        }
        setApplicationErrorMsg(msg);
        setApplicationSubmitting(false);
        return;
      }

      // Sucesso na gravação no PostgreSQL
      const createdId = data.business_id || `app-${Date.now()}`;
      const cleanCity = applicationForm.city.trim() || 'cidade';
      const newApp: Business = {
        id: createdId,
        name: applicationForm.name,
        slug: `${applicationForm.name.toLowerCase().replace(/\s+/g, '-')}-${cleanCity.toLowerCase().replace(/\s+/g, '-')}`,
        description: applicationForm.description,
        listing_type: 'service',
        service_mode: applicationForm.service_mode,
        service_radius_km: applicationForm.service_radius_km,
        category_name: cat ? cat.name : 'Serviços',
        category_slug: applicationForm.category_slug,
        whatsapp: applicationForm.whatsapp,
        neighborhood: applicationForm.neighborhood,
        city: applicationForm.city.trim() || 'Campinas',
        state: (applicationForm.state.trim() || 'SP').toUpperCase(),
        show_full_address: false,
        latitude: userLocation.lat + (Math.random() - 0.5) * 0.02,
        longitude: userLocation.lng + (Math.random() - 0.5) * 0.02,
        status: 'pending_review',
        is_verified: false,
        document_type: docType,
        document_number: cleanDoc || undefined,
        created_at: new Date().toISOString(),
        accepted_manifesto: applicationForm.accepted_manifesto,
        accepted_manifesto_at: new Date().toISOString(),
        manifesto_version: MANIFESTO_VERSION,
      };

      setBusinesses((prev) => [newApp, ...prev]);
      setApplicationSubmitted(true);
      setApplicationSubmitting(false);

      setTimeout(() => {
        setApplicationSubmitted(false);
        setShowApplicationModal(false);
        setApplicationForm({
          name: '',
          category_slug: 'eletricista',
          document_number: '',
          whatsapp: '',
          neighborhood: '',
          city: '',
          state: 'SP',
          service_mode: 'at_customer',
          service_radius_km: 20,
          description: '',
          accepted_manifesto: false,
          accepted_privacy: false,
        });
      }, 3500);
    } catch (err) {
      console.error('Erro na submissão:', err);
      setApplicationErrorMsg('Falha de conexão com o servidor. Verifique sua conexão e tente novamente.');
      setApplicationSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b0e] text-slate-100 flex flex-col selection:bg-amber-500 selection:text-black">
      {/* Top Navbar com Identidade Brasil Dark (Verde, Azul e Ouro) */}
      <header className="border-b border-[#182836] bg-[#0d151c]/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 font-bold text-lg tracking-tight text-white group">
              {/* Bandeira Oficial do Brasil Estilizada (Mesma do Favicon) */}
              <BrasilLogo size={36} className="w-9 h-9 group-hover:border-amber-400" />
              <div className="leading-tight">
                <span className="text-white font-black tracking-tight text-lg">Patriota</span>
                <span className="text-emerald-400 ml-1 font-black text-lg">Indica</span>
                <span className="text-[10px] block text-amber-400 font-bold tracking-wider uppercase flex items-center gap-1">
                  <Star className="w-2.5 h-2.5 fill-amber-400" /> Clube de Negócios
                </span>
              </div>
            </Link>

            <span className="hidden sm:inline-flex items-center text-xs px-2.5 py-1 rounded-full bg-[#070b0e] text-slate-300 border border-[#182836]">
              <span className="w-2 h-2 rounded-full bg-amber-400 inline-block mr-1.5 animate-pulse" />
              Piloto: <strong className="text-white ml-1">{userLocation.label}</strong>
            </span>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Botão Carta de Princípios (Modal Informativo) */}
            <button
              onClick={() => setShowManifestoModal(true)}
              className="text-xs px-3 py-1.5 rounded-xl border border-amber-500/30 hover:border-amber-400 bg-amber-500/10 text-amber-300 hover:text-amber-200 transition-all flex items-center gap-1.5 font-medium shadow-sm"
              title="Conheça os valores e a Carta de Princípios da Rede"
            >
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden sm:inline">Carta de Princípios</span>
            </button>

            {/* Atalho para o Painel do Lojista (Etapa 4) */}
            <Link
              href="/painel-empresa"
              className="text-xs px-3 py-1.5 rounded-xl border border-amber-900/60 hover:border-amber-600 bg-amber-950/30 text-amber-300 hover:text-amber-200 transition-all flex items-center gap-1.5 font-medium shadow-sm"
              title="Área exclusiva da empresa"
            >
              <Store className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden md:inline">Painel da Empresa</span>
            </Link>

            {/* Link direto para a Central de Triagem (Etapa 3) */}
            <Link
              href="/admin"
              className="text-xs px-3 py-1.5 rounded-xl border border-blue-900/60 hover:border-blue-700 bg-blue-950/40 text-blue-300 hover:text-white transition-all flex items-center gap-1.5 shadow-sm"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
              <span className="hidden sm:inline">Admin</span>
            </Link>

            <button
              onClick={() => setShowApplicationModal(true)}
              className="text-xs md:text-sm font-bold px-3.5 sm:px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/60 transition-all flex items-center gap-1.5 border border-amber-500/30"
            >
              <PlusCircle className="w-4 h-4 text-amber-300" />
              Quero ser indicado
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section com Toques de Dourado Solar, Azul Celeste e Verde Esmeralda */}
      <section className="relative pt-12 pb-14 px-4 border-b border-[#182836] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-950/30 via-[#070b0e] to-[#070b0e] overflow-hidden">
        {/* Iluminações sutis */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-10 right-1/4 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold bg-[#0d151c] text-amber-300 border border-amber-500/40 shadow-lg shadow-amber-950/20">
            <Award className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Rede de Afinidade: Negócios Recomendados • Patriota Indica</span>
          </div>

          <h1 className="text-3xl md:text-5xl font-black tracking-tight text-white leading-tight">
            Patriota Indica: Conecte-se com quem defende a livre iniciativa
          </h1>
          <p className="text-sm md:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Descubra e apoie eletricistas, clínicas, padarias, mecânicos e prestadores de confiança comprometidos com a família, livre iniciativa, respeito à propriedade privada e excelência no atendimento.
          </p>

          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => setShowManifestoModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-medium transition-colors"
            >
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              Conheça nossa Carta de Princípios e Compromisso Ético
            </button>
          </div>

          {/* Search Box Central com Bordas Douradas Sutis */}
          <div className="p-2.5 md:p-3.5 rounded-2xl bg-[#0d151c]/95 border border-[#182836] hover:border-amber-500/30 shadow-2xl backdrop-blur-md max-w-3xl mx-auto space-y-3 transition-colors">
            <div className="flex flex-col sm:flex-row items-center gap-2.5">
              <div className="relative flex-1 w-full">
                <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-amber-400" />
                <input
                  type="text"
                  placeholder="O que você precisa? Ex: Eletricista 24h, Padaria Cambuí..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 bg-[#070b0e] border border-[#182836] rounded-xl text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Botão de Localização GPS com destaque */}
              <button
                onClick={handleGetLocation}
                disabled={isLocating}
                className={`w-full sm:w-auto px-4 py-3 rounded-xl border text-xs md:text-sm font-semibold flex items-center justify-center gap-2 transition-all whitespace-nowrap ${
                  locationSuccess
                    ? 'bg-emerald-950/80 border-emerald-600 text-emerald-300 shadow-sm'
                    : 'bg-[#121e29] hover:bg-[#182836] border-[#182836] text-slate-200 hover:border-amber-500/40'
                }`}
              >
                <MapPin className={`w-4 h-4 ${isLocating ? 'animate-bounce text-amber-400' : 'text-amber-400'}`} />
                {isLocating ? 'Obtendo GPS...' : locationSuccess ? 'GPS Ativo' : 'Usar minha localização'}
              </button>
            </div>

            {/* Sub-filtros: Raio e Tipo */}
            <div className="flex flex-wrap items-center justify-between gap-2.5 pt-2 border-t border-[#182836] text-xs">
              <div className="flex items-center gap-1.5 text-slate-400">
                <SlidersHorizontal className="w-3.5 h-3.5 text-amber-400" />
                <span>Raio:</span>
                <button
                  type="button"
                  onClick={() => setMaxDistanceKm(null)}
                  className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                    maxDistanceKm === null
                      ? 'bg-amber-950/80 text-amber-300 border border-amber-500/60 shadow-sm'
                      : 'bg-[#070b0e] text-slate-400 hover:text-white border border-[#182836]'
                  }`}
                >
                  Brasil
                </button>
                {[15, 30, 50, 100].map((km) => (
                  <button
                    key={km}
                    type="button"
                    onClick={() => setMaxDistanceKm(km)}
                    className={`px-2.5 py-1 rounded-lg transition-colors font-medium ${
                      maxDistanceKm === km
                        ? 'bg-amber-950/80 text-amber-300 border border-amber-500/60 shadow-sm'
                        : 'bg-[#070b0e] text-slate-400 hover:text-white border border-[#182836]'
                    }`}
                  >
                    {km} km
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-1 bg-[#070b0e] p-1 rounded-xl border border-[#182836]">
                <button
                  onClick={() => setSelectedType('all')}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    selectedType === 'all' ? 'bg-[#182836] text-white font-semibold' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Todos
                </button>
                <button
                  onClick={() => setSelectedType('service')}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    selectedType === 'service' ? 'bg-emerald-950/80 text-emerald-300 font-semibold border border-emerald-800/40' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Serviços
                </button>
                <button
                  onClick={() => setSelectedType('product')}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    selectedType === 'product' ? 'bg-amber-950/80 text-amber-300 font-semibold border border-amber-800/40' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Produtos
                </button>
              </div>
            </div>
          </div>

          {/* Categorias em Pílulas com Navegação e Rolagem Horizontal */}
          <div className="relative max-w-4xl mx-auto pt-2 flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => scrollCategories('left')}
              className="shrink-0 p-2 rounded-xl bg-[#0d151c]/90 hover:bg-[#182836] border border-[#182836] hover:border-amber-500/50 text-slate-300 hover:text-white transition-all shadow-md"
              title="Rolar categorias para a esquerda"
              aria-label="Rolar para a esquerda"
            >
              <ChevronLeft className="w-4 h-4 text-amber-400" />
            </button>

            <div
              ref={categoriesRef}
              onWheel={(e) => {
                if (categoriesRef.current) {
                  if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
                  categoriesRef.current.scrollLeft += e.deltaY;
                }
              }}
              className="flex items-center gap-2 overflow-x-auto pb-1.5 scroll-smooth no-scrollbar flex-1 touch-pan-x"
            >
              <button
                onClick={() => setSelectedCategory(null)}
                className={`shrink-0 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                  selectedCategory === null
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/60 border border-amber-400/30'
                    : 'bg-[#0d151c] hover:bg-[#121e29] border border-[#182836] text-slate-300 hover:text-white'
                }`}
              >
                Todas as categorias
              </button>
              {categoriesList.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(selectedCategory === cat.slug ? null : cat.slug)}
                  className={`shrink-0 px-3.5 py-2 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all ${
                    selectedCategory === cat.slug
                      ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/60 font-semibold border border-amber-400/30'
                      : 'bg-[#0d151c] hover:bg-[#121e29] border border-[#182836] text-slate-300 hover:text-white'
                  }`}
                >
                  {CATEGORY_ICONS[cat.icon_name] || <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
                  {cat.name}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => scrollCategories('right')}
              className="shrink-0 p-2 rounded-xl bg-[#0d151c]/90 hover:bg-[#182836] border border-[#182836] hover:border-amber-500/50 text-slate-300 hover:text-white transition-all shadow-md"
              title="Rolar categorias para a direita"
              aria-label="Rolar para a direita"
            >
              <ChevronRight className="w-4 h-4 text-amber-400" />
            </button>
          </div>
        </div>
      </section>

      {/* Grid de Resultados */}
      <main className="max-w-7xl mx-auto px-4 py-8 flex-1 w-full space-y-6">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <p>
            Mostrando <strong className="text-white font-bold">{filteredBusinesses.length}</strong> empresas com curadoria aprovada em{' '}
            <strong className="text-amber-400">{userLocation.label}</strong>
          </p>
          {(selectedCategory || searchQuery || selectedType !== 'all') && (
            <button
              onClick={() => {
                setSelectedCategory(null);
                setSearchQuery('');
                setSelectedType('all');
              }}
              className="text-amber-400 hover:underline font-semibold"
            >
              Limpar filtros
            </button>
          )}
        </div>

        {/* Grid de Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBusinesses.map((business) => {
            const isCustomerService = business.service_mode === 'at_customer' || business.service_mode === 'both';

            return (
              <div
                key={business.id}
                className="group rounded-2xl bg-[#0d151c] hover:bg-[#101b24] border border-[#182836] hover:border-amber-500/40 transition-all duration-300 flex flex-col justify-between overflow-hidden shadow-xl hover:shadow-2xl"
              >
                {/* Imagem / Header do Card */}
                <div>
                  <div className="relative h-44 w-full bg-[#070b0e] overflow-hidden">
                    {business.banner_url ? (
                      <div
                        className="w-full h-full bg-cover bg-center transition-transform duration-500 group-hover:scale-105"
                        style={{ backgroundImage: `url(${business.banner_url})` }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-[#0d151c] text-slate-600">
                        <Building2 className="w-12 h-12" />
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-[#0d151c] via-[#0d151c]/30 to-transparent" />

                    {/* Badges superiores */}
                    <div className="absolute top-3 left-3 flex flex-wrap gap-1.5">
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#070b0e]/90 text-emerald-300 border border-emerald-500/30 backdrop-blur-md">
                        {business.category_name}
                      </span>
                    </div>

                    <div className="absolute top-3 right-3 flex items-center gap-1">
                      {business.accepted_manifesto && (
                        <span 
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setShowManifestoModal(true);
                          }}
                          className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 backdrop-blur-md flex items-center gap-1 cursor-pointer hover:bg-amber-500/30 transition-colors shadow-md"
                          title="Signatária da Carta de Princípios da Liberdade"
                        >
                          <ShieldCheck className="w-3 h-3 text-amber-400" />
                          Signatária
                        </span>
                      )}
                      {business.is_verified && (
                        <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-950/90 text-blue-300 border border-blue-500/40 backdrop-blur-md flex items-center gap-1 shadow-md">
                          <CheckCircle2 className="w-3 h-3 text-blue-400" />
                          Verificada
                        </span>
                      )}
                      <span className="p-1 rounded-full bg-[#070b0e]/90 text-amber-400 border border-amber-500/30" title="Selo Oficial de Curadoria">
                        <Star className="w-3 h-3 fill-amber-400" />
                      </span>
                    </div>
                  </div>

                  {/* Conteúdo do Card */}
                  <div className="p-5 space-y-3">
                    {/* Regra Inegociável 6: Distância ou Raio de Atendimento */}
                    <div>
                      {isCustomerService ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-md bg-emerald-950/70 text-emerald-300 border border-emerald-800/50">
                          <Navigation className="w-3 h-3 text-emerald-400" />
                          Atende sua região (raio de {business.service_radius_km || 20} km)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-md bg-blue-950/70 text-blue-300 border border-blue-800/50">
                          <MapPin className="w-3 h-3 text-blue-400" />
                          {business.distance_km || 2.4} km de você
                        </span>
                      )}
                    </div>

                    <h3 className="text-lg font-bold text-white group-hover:text-amber-400 transition-colors line-clamp-1">
                      {business.name}
                    </h3>

                    <p className="text-xs text-slate-400 flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-amber-400/80 shrink-0" />
                      {business.neighborhood}, {business.city}
                    </p>

                    <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                      {business.description}
                    </p>
                  </div>
                </div>

                {/* Footer do Card com CTA WhatsApp */}
                <div className="p-5 pt-0 space-y-2">
                  <a
                    href={formatWhatsAppUrl(business.whatsapp, business.name)}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => {
                      fetch(`/api/v1/go/whatsapp/${business.id}`, { keepalive: true }).catch(() => {});
                    }}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs md:text-sm shadow-md shadow-emerald-950/60 transition-all border border-amber-400/30"
                  >
                    <MessageCircle className="w-4 h-4 fill-current" />
                    Conversar no WhatsApp
                  </a>

                  <Link
                    href={`/${business.city.toLowerCase()}-${business.state.toLowerCase()}/${business.category_slug}/${business.slug}`}
                    className="w-full flex items-center justify-center gap-1 py-1.5 text-xs text-slate-400 hover:text-amber-300 transition-colors"
                  >
                    Ver perfil completo e detalhes
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>

        {/* Empty State */}
        {filteredBusinesses.length === 0 && (
          <div className="text-center py-16 space-y-4 rounded-2xl border border-[#182836] bg-[#0d151c]/60 p-8">
            <Building2 className="w-12 h-12 text-amber-400/60 mx-auto" />
            <h3 className="text-lg font-bold text-white">Nenhuma empresa encontrada com estes filtros</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Nossa triagem é rigorosa e prioriza qualidade à quantidade. Experimente aumentar o raio de busca ou
              pesquisar outra categoria.
            </p>
            <button
              onClick={() => {
                setSelectedCategory(null);
                setSearchQuery('');
                setMaxDistanceKm(null);
              }}
              className="px-4 py-2 rounded-xl bg-[#121e29] hover:bg-[#182836] border border-[#182836] text-xs text-amber-300"
            >
              Resetar busca
            </button>
          </div>
        )}
      </main>

      {/* Modal: Canal C - Candidatura ("Quero ser indicado") */}
      {showApplicationModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="bg-[#0d151c] border border-amber-500/30 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setShowApplicationModal(false)}
              className="absolute right-4 top-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-start gap-3">
              <BrasilLogo size={40} className="w-10 h-10 mt-1" />
              <div className="space-y-1">
                <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  Canal C: Candidatura Espontânea
                </span>
                <h2 className="text-xl font-bold text-white">Cadastre sua empresa para triagem</h2>
                <p className="text-xs text-slate-400">
                  Somente empresas aprovadas em nossa análise cadastral e documental aparecem na plataforma.
                </p>
              </div>
            </div>

            {applicationErrorMsg && (
              <div className="p-3.5 rounded-xl bg-red-950/70 border border-red-500/60 text-red-200 text-xs flex items-start gap-2.5 shadow-lg animate-in fade-in">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="font-bold text-red-300">Atenção ao preencher:</p>
                  <p className="text-slate-300 leading-relaxed">{applicationErrorMsg}</p>
                </div>
              </div>
            )}

            {applicationSubmitted ? (
              <div className="p-6 rounded-xl bg-emerald-950/60 border border-emerald-800/60 text-center space-y-2">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                <h3 className="text-base font-bold text-white">Candidatura Enviada!</h3>
                <p className="text-xs text-slate-300">
                  Seu registro entrou na fila de análise com status <strong className="text-amber-400">pending_review</strong>. Nossa equipe
                  conferirá o CNPJ e o WhatsApp em até 48 horas.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmitApplication} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Nome do Negócio / Fantasia *</label>
                  <input
                    required
                    type="text"
                    placeholder="Ex: Moura Refrigeração & Climatização"
                    value={applicationForm.name}
                    onChange={(e) => setApplicationForm({ ...applicationForm, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Categoria Principal *</label>
                    <select
                      value={applicationForm.category_slug}
                      onChange={(e) => setApplicationForm({ ...applicationForm, category_slug: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                    >
                      {categoriesList.map((c) => (
                        <option key={c.id} value={c.slug}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">CNPJ (ou CPF)</label>
                    <input
                      type="text"
                      placeholder="00.000.000/0001-00"
                      value={applicationForm.document_number}
                      onChange={(e) => setApplicationForm({ ...applicationForm, document_number: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">WhatsApp de Atendimento *</label>
                  <input
                    required
                    type="text"
                    placeholder="DDD + Número (ex: 19999998888)"
                    value={applicationForm.whatsapp}
                    onChange={(e) => setApplicationForm({ ...applicationForm, whatsapp: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-1">
                    <label className="block text-slate-300 font-medium mb-1">Cidade *</label>
                    <input
                      required
                      type="text"
                      placeholder="Ex: Campinas, Curitiba..."
                      value={applicationForm.city}
                      onChange={(e) => setApplicationForm({ ...applicationForm, city: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                    />
                  </div>
                  <div className="sm:col-span-1">
                    <label className="block text-slate-300 font-medium mb-1">Estado (UF) *</label>
                    <select
                      value={applicationForm.state}
                      onChange={(e) => setApplicationForm({ ...applicationForm, state: e.target.value })}
                      className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                    >
                      {BRAZIL_STATES.map((uf) => (
                        <option key={uf} value={uf}>
                          {uf}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="sm:col-span-1">
                    <label className="block text-slate-300 font-medium mb-1">Bairro / Região *</label>
                    <input
                      required
                      type="text"
                      placeholder="Ex: Centro, Cambuí..."
                      value={applicationForm.neighborhood}
                      onChange={(e) => setApplicationForm({ ...applicationForm, neighborhood: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Modo de Atendimento</label>
                    <select
                      value={applicationForm.service_mode}
                      onChange={(e) =>
                        setApplicationForm({
                          ...applicationForm,
                          service_mode: e.target.value as 'at_customer' | 'at_location' | 'both' | 'online',
                        })
                      }
                      className="w-full px-3 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                    >
                      <option value="at_customer">A domicílio (vou até o cliente)</option>
                      <option value="at_location">No meu estabelecimento</option>
                      <option value="both">Ambos</option>
                      <option value="online">100% Online / Nacional</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Raio Atendido (km)</label>
                    <input
                      type="number"
                      value={applicationForm.service_radius_km}
                      onChange={(e) =>
                        setApplicationForm({
                          ...applicationForm,
                          service_radius_km: Number(e.target.value),
                        })
                      }
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Descrição dos Serviços e Diferenciais *</label>
                  <textarea
                    required
                    rows={3}
                    placeholder="Conte sobre suas especialidades, garantia, formas de pagamento..."
                    value={applicationForm.description}
                    onChange={(e) => setApplicationForm({ ...applicationForm, description: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-[#182836] text-white focus:border-amber-500 outline-none resize-none"
                  />
                </div>

                {/* Adesão à Carta de Princípios (Blindagem Jurídica) */}
                <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-amber-400" />
                      Carta de Princípios da Liberdade *
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowManifestoModal(true)}
                      className="text-[11px] text-amber-300 hover:text-white underline font-medium"
                    >
                      Ler Carta Completa
                    </button>
                  </div>
                  <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-300">
                    <input
                      type="checkbox"
                      required
                      checked={applicationForm.accepted_manifesto}
                      onChange={(e) => setApplicationForm({ ...applicationForm, accepted_manifesto: e.target.checked })}
                      className="mt-0.5 rounded border-gray-700 text-amber-500 focus:ring-amber-500 bg-[#070b0e]"
                    />
                    <span>
                      Declaro que li e subscrevo voluntariamente a <strong>Carta de Princípios da Liberdade</strong> (livre iniciativa, direito de propriedade, ética cristã/ocidental e valorização da família).
                    </span>
                  </label>

                  {/* Consentimento Específico e Destacado LGPD (Art. 5º, II e Art. 11, I) */}
                  <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-300 pt-1 border-t border-[#182836]">
                    <input
                      type="checkbox"
                      required
                      checked={applicationForm.accepted_privacy}
                      onChange={(e) => setApplicationForm({ ...applicationForm, accepted_privacy: e.target.checked })}
                      className="mt-0.5 rounded border-gray-700 text-amber-500 focus:ring-amber-500 bg-[#070b0e]"
                    />
                    <span>
                      Declaro que li e concordo com os{' '}
                      <Link href="/termos" target="_blank" className="text-amber-400 underline font-semibold hover:text-amber-300">
                        Termos de Uso
                      </Link>{' '}
                      e a{' '}
                      <Link href="/privacidade" target="_blank" className="text-amber-400 underline font-semibold hover:text-amber-300">
                        Política de Privacidade (LGPD)
                      </Link>
                      . Na condição de titular de dados ou MEI, concedo meu consentimento específico e destacado (Art. 11, I da LGPD) para o tratamento dos dados informados e associação pública à comunidade, ciente de que posso revogar este consentimento e solicitar a exclusão de meu perfil a qualquer momento.
                    </span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={applicationSubmitting}
                  className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-bold transition-all shadow-lg shadow-emerald-950/60 border border-amber-400/40 flex items-center justify-center gap-2"
                >
                  {applicationSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                      <span>Gravando Candidatura no Sistema...</span>
                    </>
                  ) : (
                    <span>Enviar para Análise</span>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Modal da Carta de Princípios e Valores da Liberdade */}
      <ManifestoModal
        isOpen={showManifestoModal}
        onClose={() => setShowManifestoModal(false)}
        showAcceptButton={showApplicationModal && !applicationForm.accepted_manifesto}
        onAccept={() => setApplicationForm((prev) => ({ ...prev, accepted_manifesto: true }))}
      />

      {/* Footer */}
      <footer className="border-t border-[#182836] bg-[#070b0e] text-slate-400 text-xs py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <BrasilLogo size={20} className="w-5 h-5 !rounded-md" />
            <span>© 2026 Patriota Indica. A rede de confiança da livre iniciativa e valores tradicionais.</span>
          </div>
          <div className="flex gap-4">
            <button onClick={() => setShowManifestoModal(true)} className="hover:text-amber-300">
              Carta de Princípios
            </button>
            <Link href="/termos" className="hover:text-amber-300">Termos de Uso</Link>
            <Link href="/privacidade" className="hover:text-amber-300">Política de Privacidade (LGPD)</Link>
            <Link href="/painel-empresa" className="text-amber-400 hover:underline">Painel da Empresa</Link>
            <Link href="/admin" className="text-blue-400 hover:underline">Central do Administrador</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
