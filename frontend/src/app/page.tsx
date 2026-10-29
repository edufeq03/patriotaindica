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
  Globe,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  CreditCard,
  Gift,
  Users,
  Briefcase
} from 'lucide-react';
import { INITIAL_BUSINESSES, INITIAL_CATEGORIES, calculateDistanceKm } from '@/lib/mockData';
import { Business, Category, ListingType } from '@/lib/types';
import ManifestoModal, { MANIFESTO_VERSION } from '@/components/ManifestoModal';
import BusinessJobsModal from '@/components/BusinessJobsModal';
import { getBusinessBannerUrl } from '@/lib/categoryBanners';

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
  const [hiringOnly, setHiringOnly] = useState(false);
  const [selectedJobsBusiness, setSelectedJobsBusiness] = useState<any>(null);

  // Paginação de cards na vitrine
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(12);
  const resultsRef = useRef<HTMLElement>(null);

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
  const [submittedWhatsapp, setSubmittedWhatsapp] = useState('');

  // Form State para Candidatura (Canal C)
  const [applicationForm, setApplicationForm] = useState({
    name: '',
    category_slug: 'eletricista',
    custom_category: '',
    document_number: '',
    referred_by_code: '',
    whatsapp: '',
    neighborhood: '',
    city: '',
    state: 'SP',
    service_mode: 'at_customer' as 'at_customer' | 'at_location' | 'both' | 'online',
    serves_at_location: true,
    serves_at_customer: true,
    serves_online: false,
    service_radius_km: 20,
    description: '',
    accepted_manifesto: false,
    accepted_privacy: false,
  });
  const [applicationSubmitted, setApplicationSubmitted] = useState(false);
  const [applicationSubmitting, setApplicationSubmitting] = useState(false);
  const [applicationErrorMsg, setApplicationErrorMsg] = useState<string | null>(null);
  const [referralBadge, setReferralBadge] = useState<string | null>(null);
  const [showManualReferralInput, setShowManualReferralInput] = useState(false);

  // Leitura de parâmetros de indicação ou atalhos na URL (?ref=... ou ?action=nova-empresa)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      let ref = params.get('ref');
      if (ref && (ref.trim().toLowerCase() === 'none' || ref.trim().toLowerCase() === 'null')) {
        ref = null;
      }
      if (!ref) {
        try {
          const stored = sessionStorage.getItem('patriotaindica_ref');
          if (stored && stored.toLowerCase() !== 'none' && stored.toLowerCase() !== 'null') {
            ref = stored;
          }
        } catch {}
      }
      if (ref) {
        const cleanRef = ref.trim().toUpperCase();
        try {
          sessionStorage.setItem('patriotaindica_ref', cleanRef);
        } catch {}
        setReferralBadge(cleanRef);
        setApplicationForm((prev) => ({ ...prev, referred_by_code: cleanRef }));
      }
      if (params.get('action') === 'nova-empresa' || params.get('candidatura') === 'true') {
        setShowApplicationModal(true);
      }
    }
  }, []);

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
        const searchRes = await fetch('/api/v1/search?page=1&limit=100');
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

        // Filtro por empresas contratando (T-V2.3)
        if (hiringOnly) {
          const isHiring = (b as any).hiring?.active || (typeof (b as any).hiring?.count === 'number' && (b as any).hiring.count > 0);
          if (!isHiring) return false;
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
  }, [businesses, userLocation, searchQuery, selectedCategory, selectedType, maxDistanceKm, hiringOnly]);

  // Resetar página ao alterar filtros
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedCategory, selectedType, maxDistanceKm, hiringOnly]);

  // Cálculos de Paginação
  const totalPages = Math.max(1, Math.ceil(filteredBusinesses.length / itemsPerPage));

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, currentPage]);

  const paginatedBusinesses = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredBusinesses.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredBusinesses, currentPage, itemsPerPage]);

  const pageNumbers = useMemo(() => {
    const pages: (number | string)[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      if (currentPage <= 4) {
        pages.push(1, 2, 3, 4, 5, '...', totalPages);
      } else if (currentPage >= totalPages - 3) {
        pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
      }
    }
    return pages;
  }, [totalPages, currentPage]);

  const goToPage = (pageNumber: number) => {
    const target = Math.max(1, Math.min(pageNumber, totalPages));
    setCurrentPage(target);
    if (resultsRef.current) {
      const topOffset = resultsRef.current.getBoundingClientRect().top + window.scrollY - 90;
      window.scrollTo({ top: topOffset, behavior: 'smooth' });
    }
  };

  // Submeter Candidatura Real (Canal C - "Quero ser indicado" -> PostgreSQL)
  const handleSubmitApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    setApplicationSubmitting(true);
    setApplicationErrorMsg(null);

    const isCustom = applicationForm.category_slug === 'outra';
    const cat = isCustom ? null : categoriesList.find((c) => c.slug === applicationForm.category_slug);
    const isUuid = cat?.id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(cat.id);

    if (isCustom && (!applicationForm.custom_category || !applicationForm.custom_category.trim())) {
      setApplicationErrorMsg("Por favor, digite o nome da sua especialidade ou serviço.");
      setApplicationSubmitting(false);
      return;
    }

    const customName = applicationForm.custom_category?.trim();

    // Limpar documento: se vazio, envia null para não disparar validação de checksum
    const rawDoc = applicationForm.document_number?.trim();
    const cleanDoc = rawDoc ? rawDoc.replace(/\D/g, '') : null;
    const docType = cleanDoc && cleanDoc.length === 11 ? 'CPF' : 'CNPJ';

    if (!applicationForm.serves_at_location && !applicationForm.serves_at_customer && !applicationForm.serves_online) {
      setApplicationErrorMsg('Selecione ao menos um método de atendimento (No Estabelecimento, A Domicílio ou Online).');
      setApplicationSubmitting(false);
      return;
    }

    if (applicationForm.serves_at_customer) {
      const radius = Number(applicationForm.service_radius_km);
      if (isNaN(radius) || radius < 1) {
        setApplicationErrorMsg('Por favor, informe um raio de deslocamento válido (mínimo de 1 km).');
        setApplicationSubmitting(false);
        return;
      }
      if (radius > 150) {
        setApplicationErrorMsg('O raio máximo de atendimento a domicílio é de 150 km. Para atendimento em outras regiões do país, selecione também a opção "Online / Nacional".');
        setApplicationSubmitting(false);
        return;
      }
    }

    let effectiveMode: 'at_location' | 'at_customer' | 'both' | 'online' = 'at_location';
    if (applicationForm.serves_at_customer && applicationForm.serves_at_location) {
      effectiveMode = 'both';
    } else if (applicationForm.serves_at_customer) {
      effectiveMode = 'at_customer';
    } else if (applicationForm.serves_online && !applicationForm.serves_at_location) {
      effectiveMode = 'online';
    }

    if (!applicationForm.accepted_manifesto) {
      setApplicationErrorMsg("É necessário aceitar e subscrever a Carta de Princípios da Liberdade.");
      setApplicationSubmitting(false);
      return;
    }

    if (!applicationForm.accepted_privacy) {
      setApplicationErrorMsg("É necessário concordar com os Termos de Uso e a Política de Privacidade (LGPD).");
      setApplicationSubmitting(false);
      return;
    }

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
      service_mode: effectiveMode,
      serves_at_location: applicationForm.serves_at_location,
      serves_at_customer: applicationForm.serves_at_customer,
      serves_online: applicationForm.serves_online,
      service_radius_km: applicationForm.serves_at_customer ? Math.min(150, Math.max(1, Number(applicationForm.service_radius_km) || 20)) : null,
      category_ids: isUuid && cat ? [cat.id] : [],
      primary_category_id: isUuid && cat ? cat.id : null,
      proposed_niche: isCustom ? customName : ((!isUuid && cat) ? cat.name : null),
      referred_by_code: applicationForm.referred_by_code.trim() || null,
      show_full_address: false,
      consent_carta_principios: Boolean(applicationForm.accepted_manifesto),
      consent_termos: Boolean(applicationForm.accepted_privacy),
      consent_privacidade: Boolean(applicationForm.accepted_privacy),
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
        let msg = res.status >= 500
          ? 'O servidor de banco de dados está temporariamente inacessível. Verifique se o backend está ativo ou tente novamente em instantes.'
          : 'Erro ao cadastrar empresa. Verifique os dados informados.';

        if (data?.detail) {
          if (typeof data.detail === 'string') {
            msg = data.detail;
          } else if (Array.isArray(data.detail)) {
            const fieldLabels: Record<string, string> = {
              consent_carta_principios: 'Carta de Princípios',
              consent_termos: 'Termos de Serviço',
              consent_privacidade: 'Política de Privacidade',
              name: 'Nome do Negócio',
              whatsapp: 'WhatsApp de Atendimento',
              neighborhood: 'Bairro',
              city: 'Cidade',
              state: 'Estado (UF)',
              document_number: 'CNPJ / CPF',
              description: 'Descrição',
              service_radius_km: 'Raio de Atendimento',
            };

            msg = data.detail
              .map((err: any) => {
                const fieldName = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : '';
                const label = fieldLabels[fieldName] || fieldName;
                if (err.msg === 'Field required') {
                  return `O campo "${label}" é obrigatório.`;
                }
                if (label) {
                  return `${label}: ${err.msg || err.message}`;
                }
                return err.msg || err.message;
              })
              .join(' | ');
          }
        } else if (data?.message) {
          msg = data.message;
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
        service_mode: effectiveMode,
        serves_at_location: applicationForm.serves_at_location,
        serves_at_customer: applicationForm.serves_at_customer,
        serves_online: applicationForm.serves_online,
        service_radius_km: applicationForm.serves_at_customer ? applicationForm.service_radius_km : undefined,
        category_name: isCustom ? (customName || 'Serviços') : (cat ? cat.name : 'Serviços'),
        category_slug: isCustom ? (customName ? customName.toLowerCase().replace(/\s+/g, '-') : 'servicos') : applicationForm.category_slug,
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
      setSubmittedWhatsapp(applicationForm.whatsapp);
      setApplicationSubmitted(true);
      setApplicationSubmitting(false);
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

            {/* Atalho para Vagas de Emprego (Sprint V3) */}
            <Link
              href="/vagas"
              className="text-xs px-2.5 py-1.5 rounded-xl border border-amber-500/30 hover:border-amber-400 bg-amber-500/10 text-amber-300 hover:text-white transition-all flex items-center gap-1.5 font-bold shadow-sm"
              title="Ver vagas de trabalho abertas na rede"
            >
              <Briefcase className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden sm:inline">Vagas</span>
            </Link>

            {/* Atalho para o Painel da Empresa */}
            <Link
              href="/painel-empresa"
              className="text-xs px-2.5 sm:px-3 py-1.5 rounded-xl border border-amber-900/60 hover:border-amber-600 bg-amber-950/30 text-amber-300 hover:text-amber-200 transition-all flex items-center gap-1.5 font-semibold shadow-sm"
              title="Área exclusiva da empresa parceira"
            >
              <Store className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden sm:inline">Painel da Empresa</span>
              <span className="sm:hidden">Painel</span>
            </Link>

            {/* Atalho para o Painel Admin */}
            <Link
              href="/admin"
              className="text-xs px-2 sm:px-2.5 py-1.5 rounded-xl border border-slate-700/80 hover:border-slate-500 bg-slate-900/80 text-slate-300 hover:text-white transition-all flex items-center gap-1.5 font-medium shadow-sm"
              title="Portal da Moderação e Administração"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="hidden sm:inline">Admin</span>
            </Link>

            {/* Link para Planos */}
            <a
              href="#planos"
              className="text-xs px-3 py-1.5 rounded-xl border border-amber-500/20 hover:border-amber-500/40 bg-amber-500/5 text-amber-300 hover:text-white transition-all flex items-center gap-1.5 font-medium shadow-sm hidden lg:flex"
            >
              <Award className="w-3.5 h-3.5 text-amber-400" />
              <span>Planos do Clube</span>
            </a>

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

      {/* Banner de Indicação Ativa */}
      {referralBadge && (
        <div className="bg-gradient-to-r from-emerald-950/80 via-[#0d151c] to-emerald-950/80 border-b border-emerald-500/30 py-2.5 px-4 text-center text-xs text-emerald-200 flex items-center justify-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>
            Convite Especial: Você foi indicado por uma empresa parceira da Rede Patriota. Sua candidatura terá análise prioritária na curadoria!
          </span>
          <button
            onClick={() => setShowApplicationModal(true)}
            className="ml-2 px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] shadow-sm"
          >
            Cadastrar Minha Empresa
          </button>
        </div>
      )}

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
                <button
                  type="button"
                  onClick={() => setHiringOnly(!hiringOnly)}
                  className={`px-3 py-1 rounded-lg transition-all flex items-center gap-1.5 ${
                    hiringOnly
                      ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                      : 'text-amber-400/90 hover:text-amber-300 hover:bg-[#182836]'
                  }`}
                  title="Filtrar empresas com vagas de emprego abertas"
                >
                  <Briefcase className="w-3.5 h-3.5" />
                  <span>Contratando</span>
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
      <main ref={resultsRef} id="vitrine" className="max-w-7xl mx-auto px-4 py-8 flex-1 w-full space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-400">
          <div>
            Mostrando{' '}
            <strong className="text-white font-bold">
              {filteredBusinesses.length === 0
                ? 0
                : `${(currentPage - 1) * itemsPerPage + 1}–${Math.min(currentPage * itemsPerPage, filteredBusinesses.length)}`}
            </strong>{' '}
            de <strong className="text-white font-bold">{filteredBusinesses.length}</strong> empresas com curadoria aprovada em{' '}
            <strong className="text-amber-400">{userLocation.label}</strong>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <span className="text-[11px] text-slate-500">Exibir:</span>
              {[6, 12, 24].map((size) => (
                <button
                  key={size}
                  onClick={() => {
                    setItemsPerPage(size);
                    setCurrentPage(1);
                  }}
                  className={`px-2 py-0.5 rounded text-xs transition-colors ${
                    itemsPerPage === size
                      ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40'
                      : 'text-slate-400 hover:text-white bg-[#0d151c] border border-[#182836]'
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>

            {(selectedCategory || searchQuery || selectedType !== 'all') && (
              <button
                onClick={() => {
                  setSelectedCategory(null);
                  setSearchQuery('');
                  setSelectedType('all');
                  setCurrentPage(1);
                }}
                className="text-amber-400 hover:underline font-semibold"
              >
                Limpar filtros
              </button>
            )}
          </div>
        </div>

        {/* Grid de Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {paginatedBusinesses.map((business) => {
            const isCustomerService = business.service_mode === 'at_customer' || business.service_mode === 'both';
            const cityParam = (business.city || 'brasil')
              .toLowerCase()
              .normalize('NFD')
              .replace(/[\u0300-\u036f]/g, '')
              .replace(/[^a-z0-9]+/g, '-')
              .replace(/^-+|-+$/g, '');
            const stateParam = (business.state || 'br').toLowerCase();
            const catParam = (business.category_slug || 'servicos')
              .toLowerCase()
              .normalize('NFD')
              .replace(/[\u0300-\u036f]/g, '')
              .replace(/[^a-z0-9]+/g, '-')
              .replace(/^-+|-+$/g, '');
            const profileUrl = `/${cityParam}-${stateParam}/${catParam}/${business.slug}`;

            return (
              <div
                key={business.id}
                className="group rounded-2xl bg-[#0d151c] hover:bg-[#101b24] border border-[#182836] hover:border-amber-500/40 transition-all duration-300 flex flex-col justify-between overflow-hidden shadow-xl hover:shadow-2xl"
              >
                {/* Imagem / Header do Card */}
                <div>
                  <div className="relative h-44 w-full bg-[#070b0e] overflow-hidden">
                    <Link href={profileUrl} className="block w-full h-full">
                      <div
                        className="w-full h-full bg-cover bg-center transition-transform duration-500 group-hover:scale-105"
                        style={{ backgroundImage: `url(${getBusinessBannerUrl(business)})` }}
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-[#0d151c] via-[#0d151c]/30 to-transparent" />
                    </Link>

                    {/* Badges superiores */}
                    <div className="absolute top-3 left-3 flex flex-wrap gap-1.5 pointer-events-none">
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#070b0e]/90 text-emerald-300 border border-emerald-500/30 backdrop-blur-md">
                        {business.category_name}
                      </span>
                    </div>

                    <div className="absolute top-3 right-3 flex items-center gap-1 z-10">
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
                    {/* Selos de Modalidade de Atendimento Multi-Canal */}
                    <div className="flex flex-wrap gap-1.5">
                      {(business.serves_at_customer || business.service_mode === 'at_customer' || business.service_mode === 'both') && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-emerald-950/70 text-emerald-300 border border-emerald-800/50" title="Atende a domicílio no cliente">
                          <Navigation className="w-3 h-3 text-emerald-400" />
                          A domicílio ({business.service_radius_km || 20} km)
                        </span>
                      )}
                      {(business.serves_at_location || business.service_mode === 'at_location' || business.service_mode === 'both') && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-blue-950/70 text-blue-300 border border-blue-800/50" title="Atendimento presencial no estabelecimento">
                          <MapPin className="w-3 h-3 text-blue-400" />
                          {business.distance_km ? `${business.distance_km} km` : 'No local'}
                        </span>
                      )}
                      {(business.serves_online || business.service_mode === 'online') && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-950/70 text-amber-300 border border-amber-800/50" title="Atende clientes remotamente ou entrega nacional">
                          <Globe className="w-3 h-3 text-amber-400" />
                          Online Nacional
                        </span>
                      )}
                    </div>

                    <Link href={profileUrl}>
                      <h3 className="text-lg font-bold text-white group-hover:text-amber-400 transition-colors line-clamp-1 cursor-pointer">
                        {business.name}
                      </h3>
                    </Link>

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
                  {/* Selo e Ação de Vagas Abertas (T-V2.3) */}
                  {Boolean((business as any).hiring?.active || (business as any).hiring?.count > 0) && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setSelectedJobsBusiness(business);
                      }}
                      className="w-full px-3 py-2 rounded-xl bg-gradient-to-r from-amber-500/15 via-emerald-500/15 to-amber-500/15 border border-amber-500/40 hover:border-amber-400 text-amber-300 hover:text-white text-xs font-bold flex items-center justify-between gap-1.5 transition-all shadow-sm group/job"
                    >
                      <span className="flex items-center gap-1.5">
                        <Briefcase className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span>
                          Contratando ({(business as any).hiring.count} {(business as any).hiring.count === 1 ? 'vaga' : 'vagas'})
                        </span>
                      </span>
                      <span className="text-[11px] text-slate-300 font-normal group-hover/job:underline flex items-center gap-0.5">
                        Ver {(business as any).hiring.titles?.[0] ? `"${(business as any).hiring.titles[0]}"` : 'oportunidades'} →
                      </span>
                    </button>
                  )}

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
                    href={profileUrl}
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

        {/* Controles de Paginação */}
        {totalPages > 1 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 border-t border-[#182836]">
            <p className="text-xs text-slate-400">
              Página <span className="font-semibold text-white">{currentPage}</span> de{' '}
              <span className="font-semibold text-white">{totalPages}</span> ({filteredBusinesses.length} empresas encontradas)
            </p>

            <div className="flex items-center gap-1.5 flex-wrap justify-center">
              <button
                onClick={() => goToPage(currentPage - 1)}
                disabled={currentPage === 1}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#0d151c] border border-[#182836] text-slate-300 hover:text-white hover:border-amber-500/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
                title="Página anterior"
              >
                <ChevronLeft className="w-4 h-4" />
                <span className="hidden sm:inline">Anterior</span>
              </button>

              <div className="flex items-center gap-1">
                {pageNumbers.map((page, idx) => {
                  if (page === '...') {
                    return (
                      <span key={`ellipsis-${idx}`} className="px-2 py-1 text-xs text-slate-500">
                        ...
                      </span>
                    );
                  }
                  const pageNum = page as number;
                  const isActive = currentPage === pageNum;
                  return (
                    <button
                      key={`page-${pageNum}`}
                      onClick={() => goToPage(pageNum)}
                      className={`min-w-[34px] h-8 px-2.5 rounded-lg text-xs font-bold transition-all ${
                        isActive
                          ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                          : 'bg-[#0d151c] border border-[#182836] text-slate-300 hover:text-white hover:border-amber-500/40'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>

              <button
                onClick={() => goToPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#0d151c] border border-[#182836] text-slate-300 hover:text-white hover:border-amber-500/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
                title="Próxima página"
              >
                <span className="hidden sm:inline">Próxima</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Empty State */}
        {filteredBusinesses.length === 0 && (
          <div className="text-center py-16 space-y-4 rounded-2xl border border-[#182836] bg-[#0d151c]/60 p-8 max-w-2xl mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-400">
              <Building2 className="w-8 h-8" />
            </div>
            {businesses.length === 0 ? (
              <>
                <h3 className="text-xl font-bold text-white">Nenhuma empresa cadastrada no momento</h3>
                <p className="text-xs text-slate-300 max-w-md mx-auto leading-relaxed">
                  Estamos iniciando nossa rede de empresas recomendadas e confiáveis. Seja um dos primeiros profissionais ou lojistas a cadastrar sua marca na plataforma!
                </p>
                <div className="pt-2">
                  <button
                    onClick={() => setShowApplicationModal(true)}
                    className="px-6 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all cursor-pointer"
                  >
                    Cadastrar Minha Empresa Agora
                  </button>
                </div>
              </>
            ) : (
              <>
                <h3 className="text-lg font-bold text-white">Nenhuma empresa encontrada com estes filtros</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Nossa triagem é rigorosa e prioriza qualidade à quantidade. Experimente aumentar o raio de busca ou pesquisar outra categoria.
                </p>
                <button
                  onClick={() => {
                    setSelectedCategory(null);
                    setSearchQuery('');
                    setMaxDistanceKm(null);
                    setSelectedType('all');
                  }}
                  className="px-4 py-2 rounded-xl bg-[#121e29] hover:bg-[#182836] border border-[#182836] text-xs text-amber-300 cursor-pointer"
                >
                  Resetar busca
                </button>
              </>
            )}
          </div>
        )}

        {/* SEÇÃO OFICIAL: PLANOS DE ADESÃO & CLUBE DE NEGÓCIOS PATRIOTA */}
        <section id="planos" className="mt-20 pt-16 border-t border-[#182836] space-y-12">
          {/* Header da Seção */}
          <div className="text-center space-y-4 max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-bold uppercase tracking-wider">
              <Award className="w-4 h-4 text-amber-400" />
              <span>Clube de Negócios Patriota</span>
            </div>
            <h2 className="text-2xl md:text-4xl font-black text-white tracking-tight">
              Visibilidade Garantida com Retorno Real para o seu Negócio
            </h2>
            <p className="text-xs md:text-sm text-slate-300 leading-relaxed">
              Sem comissões ocultas sobre suas vendas, sem algoritmos que sabotam seu alcance e sem intermediários.
              Conecte-se diretamente a clientes qualificados que preferem comprar e contratar de quem defende a livre iniciativa.
            </p>
          </div>

          {/* Destaques Exclusivos de Lançamento */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-2xl bg-[#0d151c] border border-amber-500/20 flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 shrink-0">
                <Store className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-white">Múltiplos Negócios sem custo extra</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Contabilidade, artesanato ou estética? Cadastre quantas atividades você gerenciar sob a mesma assinatura de proprietário.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d151c] border border-emerald-500/20 flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 shrink-0">
                <Gift className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-white">Ganhe 1 Mês Grátis por Amigo</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Cada empresário amigo que se cadastrar com seu código adiciona <strong>+30 dias gratuitos</strong> na sua assinatura.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d151c] border border-blue-500/20 flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400 shrink-0">
                <CreditCard className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-white">Mercado Pago: Pix ou até 12x</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Ativação imediata via Pix ou facilidade de parcelamento em até 12 vezes no cartão de crédito.
                </p>
              </div>
            </div>
          </div>

          {/* Grid dos 3 Planos */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {/* 1. Plano Mensal */}
            <div className="rounded-3xl bg-[#0d151c] border border-[#182836] p-6 flex flex-col justify-between space-y-6 hover:border-slate-600 transition-all">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300">
                    Sem Fidelidade
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">1 mês</span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Plano Mensal</h3>
                  <p className="text-xs text-slate-400 mt-1">Flexibilidade total para divulgar seu negócio.</p>
                </div>
                <div className="pt-2 border-t border-[#182836]">
                  <div className="flex items-baseline gap-1">
                    <span className="text-xs text-slate-400">R$</span>
                    <span className="text-3xl font-black text-white">15,00</span>
                    <span className="text-xs text-slate-400">/mês</span>
                  </div>
                  <span className="text-[11px] text-slate-500 block mt-0.5">Cobrança mensal avulsa</span>
                </div>
                <ul className="space-y-2.5 text-xs text-slate-300 pt-2">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Perfil verificado no Marketplace</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Botão direto para seu WhatsApp</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Múltiplos negócios no mesmo CPF/CNPJ</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Indique amigos e ganhe meses grátis</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => setShowApplicationModal(true)}
                className="w-full py-3 rounded-xl bg-[#121e29] hover:bg-[#182836] border border-[#182836] hover:border-amber-500/40 text-amber-300 font-bold text-xs transition-all flex items-center justify-center gap-1.5"
              >
                <span>Quero me Candidatar</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* 2. Plano Semestral */}
            <div className="rounded-3xl bg-[#0d151c] border border-blue-500/30 p-6 flex flex-col justify-between space-y-6 hover:border-blue-400 transition-all shadow-lg shadow-blue-950/20">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
                    Economize 13%
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">6 meses</span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Plano Semestral</h3>
                  <p className="text-xs text-slate-400 mt-1">Estabilidade contínua para consolidar sua presença.</p>
                </div>
                <div className="pt-2 border-t border-[#182836]">
                  <div className="flex items-baseline gap-1">
                    <span className="text-xs text-slate-400">R$</span>
                    <span className="text-3xl font-black text-white">12,99</span>
                    <span className="text-xs text-slate-400">/mês</span>
                  </div>
                  <span className="text-[11px] text-blue-300 block mt-0.5">R$ 77,94 a cada 6 meses</span>
                </div>
                <ul className="space-y-2.5 text-xs text-slate-300 pt-2">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Tudo incluído no Plano Mensal</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Economia garantida de 13%</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>6 meses de visibilidade garantida</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Acesso ao Painel com métricas de cliques</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => setShowApplicationModal(true)}
                className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition-all shadow-md shadow-blue-950/40 flex items-center justify-center gap-1.5"
              >
                <span>Escolher Semestral</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* 3. Plano Anual (Destaque Patriota) */}
            <div className="rounded-3xl bg-gradient-to-b from-[#111c25] to-[#0a1118] border-2 border-amber-500 p-6 flex flex-col justify-between space-y-6 relative shadow-2xl shadow-amber-500/10">
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-amber-500 to-amber-400 text-black text-[11px] font-black uppercase tracking-wider shadow-md whitespace-nowrap">
                ⭐ Mais Escolhido • 33% OFF
              </div>
              <div className="space-y-4 pt-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/40">
                    Menos de R$ 0,33 / dia
                  </span>
                  <span className="text-[11px] text-amber-300 font-bold">12 meses</span>
                </div>
                <div>
                  <h3 className="text-lg font-black text-white flex items-center gap-1.5">
                    Plano Anual
                    <Sparkles className="w-4 h-4 text-amber-400" />
                  </h3>
                  <p className="text-xs text-slate-300 mt-1">O melhor custo-benefício para empreendedores patriotas.</p>
                </div>
                <div className="pt-2 border-t border-amber-500/20">
                  <div className="flex items-baseline gap-1">
                    <span className="text-xs text-amber-400 font-bold">R$</span>
                    <span className="text-4xl font-black text-amber-400">9,99</span>
                    <span className="text-xs text-slate-400">/mês</span>
                  </div>
                  <span className="text-[11px] text-amber-200/80 block mt-0.5">Em até 12x de R$ 9,99 (ou R$ 119,88/ano)</span>
                </div>
                <ul className="space-y-2.5 text-xs text-slate-200 pt-2">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span><strong>Selo Destaque Ouro</strong> nas buscas</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Prioridade máxima na curadoria local</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Múltiplos negócios cobertos</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Programa Indique e Ganhe ativado (+30 dias)</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Suporte VIP e selo na vitrine</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => setShowApplicationModal(true)}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-400 hover:to-amber-300 text-black font-black text-xs transition-all shadow-lg shadow-amber-950/60 flex items-center justify-center gap-2"
              >
                <span>Garantir Vaga por R$ 9,99/mês</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Banner de Indicação com Código */}
          <div className="p-6 rounded-3xl bg-gradient-to-r from-emerald-950/40 via-[#0d151c] to-amber-950/40 border border-emerald-500/30 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-2 text-center md:text-left">
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 inline-flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" />
                Programa Indique & Ganhe
              </span>
              <h3 className="text-lg md:text-xl font-bold text-white">
                Tem amigos empresários que compartilham dos seus valores?
              </h3>
              <p className="text-xs text-slate-300 max-w-xl">
                Ajude a fortalecer o comércio livre. Compartilhe seu link de indicação gerado no Painel da Empresa e ganhe <strong>1 mês grátis (+30 dias)</strong> para cada amigo que se cadastrar e ativar o plano!
              </p>
            </div>
            <Link
              href="/painel-empresa"
              className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition-all shadow-lg shadow-emerald-950/50 shrink-0 flex items-center gap-2"
            >
              <span>Acessar Meu Painel e Link</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
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
              <div className="p-4 rounded-xl bg-red-950/70 border border-red-500/60 text-red-200 text-xs flex items-start gap-2.5 shadow-lg animate-in fade-in">
                <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div className="space-y-2 flex-1">
                  <div>
                    <p className="font-bold text-red-300">Atenção ao preencher:</p>
                    <p className="text-slate-300 leading-relaxed">{applicationErrorMsg}</p>
                  </div>
                  {applicationErrorMsg.includes('já possui cadastro') && (
                    <div className="pt-1 border-t border-red-900/40">
                      <p className="text-[11px] text-amber-300 mb-2">
                        Esta empresa já está em nosso banco de dados. Você pode acessá-la diretamente pelo painel:
                      </p>
                      <Link
                        href={`/painel-empresa?phone=${encodeURIComponent(applicationForm.whatsapp)}`}
                        onClick={() => setShowApplicationModal(false)}
                        className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors shadow-md"
                      >
                        Acessar Painel do Empresário →
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            )}

            {applicationSubmitted ? (
              <div className="p-6 rounded-xl bg-emerald-950/60 border border-emerald-800/60 text-center space-y-4 animate-in fade-in">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
                <div className="space-y-1">
                  <h3 className="text-lg font-bold text-white">Cadastro Realizado com Sucesso!</h3>
                  <p className="text-xs text-slate-300 max-w-sm mx-auto leading-relaxed">
                    Sua empresa foi cadastrada com status <strong className="text-amber-400 font-semibold">Em Análise</strong>. Você já pode acessar seu painel para gerenciar suas informações e conhecer os planos de adesão.
                  </p>
                </div>
                <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-2.5">
                  <Link
                    href={`/painel-empresa?phone=${encodeURIComponent(submittedWhatsapp || applicationForm.whatsapp)}`}
                    onClick={() => {
                      setShowApplicationModal(false);
                      setApplicationSubmitted(false);
                    }}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors shadow-lg"
                  >
                    Ir para o Painel da Empresa →
                  </Link>
                  <button
                    onClick={() => {
                      setShowApplicationModal(false);
                      setApplicationSubmitted(false);
                    }}
                    className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-[#121e29] hover:bg-[#182836] border border-[#182836] text-slate-300 text-xs"
                  >
                    Concluir e Fechar
                  </button>
                </div>
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
                      <option value="outra" className="font-semibold text-amber-400">
                        ➕ Outra categoria / Não encontrei meu serviço...
                      </option>
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
                    <p className="text-[10px] text-slate-500 mt-1">Multi-negócios: Você pode cadastrar mais de uma empresa/atividade com o mesmo CPF/CNPJ.</p>
                  </div>
                </div>

                {applicationForm.category_slug === 'outra' && (
                  <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/50 space-y-1.5">
                    <label className="block text-amber-300 font-semibold text-xs flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                      Qual é o seu serviço ou especialidade? *
                    </label>
                    <input
                      required
                      type="text"
                      placeholder="Ex: Adestrador de Cães, Psicólogo, Fisioterapeuta, Fotógrafo, Tatuador..."
                      value={applicationForm.custom_category || ''}
                      onChange={(e) => setApplicationForm({ ...applicationForm, custom_category: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#070b0e] border border-amber-500/60 text-white placeholder-slate-500 focus:border-amber-400 outline-none text-xs"
                    />
                    <p className="text-[11px] text-slate-400">
                      Sua especialidade será cadastrada automaticamente no sistema e avaliada pela curadoria.
                    </p>
                  </div>
                )}

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

                {/* Métodos de Atendimento Multi-Seleção (Checkboxes) */}
                <div className="space-y-2.5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <label className="block text-slate-300 font-medium text-sm">
                      Métodos de Atendimento *
                    </label>
                    <span className="text-[11px] text-amber-400 font-medium">
                      (Selecione todas as formas que você atua)
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {/* Checkbox 1: No Estabelecimento */}
                    <label
                      className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        applicationForm.serves_at_location
                          ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                          : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={applicationForm.serves_at_location}
                        onChange={(e) =>
                          setApplicationForm({
                            ...applicationForm,
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
                          Atendimento no balcão / loja física
                        </span>
                      </div>
                    </label>

                    {/* Checkbox 2: A Domicílio */}
                    <label
                      className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        applicationForm.serves_at_customer
                          ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                          : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={applicationForm.serves_at_customer}
                        onChange={(e) =>
                          setApplicationForm({
                            ...applicationForm,
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
                          Vou até o cliente na região
                        </span>
                      </div>
                    </label>

                    {/* Checkbox 3: 100% Online */}
                    <label
                      className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-all ${
                        applicationForm.serves_online
                          ? 'bg-amber-500/10 border-amber-500/70 text-white shadow-sm ring-1 ring-amber-500/30'
                          : 'bg-[#070b0e] border-[#182836] text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={applicationForm.serves_online}
                        onChange={(e) =>
                          setApplicationForm({
                            ...applicationForm,
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
                          Atendimento remoto em todo o Brasil
                        </span>
                      </div>
                    </label>
                  </div>

                  {/* Se atende a domicílio, exibe campo para configurar o raio de deslocamento */}
                  {applicationForm.serves_at_customer && (
                    <div className="p-3.5 rounded-xl bg-[#091118] border border-emerald-800/40 space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <span className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                            <Navigation className="w-3.5 h-3.5 text-emerald-400" />
                            Raio Atendido a Domicílio (Máximo 150 km)
                          </span>
                          <p className="text-[11px] text-slate-400">
                            Distância máxima que sua equipe se desloca a partir da sua base
                          </p>
                        </div>
                        <div className="flex items-center gap-2 self-start sm:self-auto">
                          <input
                            type="number"
                            min={1}
                            max={150}
                            value={applicationForm.service_radius_km || ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              if (val === '') {
                                setApplicationForm({ ...applicationForm, service_radius_km: 0 });
                                return;
                              }
                              let num = parseInt(val, 10);
                              if (isNaN(num)) num = 1;
                              if (num > 150) num = 150;
                              if (num < 1) num = 1;
                              setApplicationForm({ ...applicationForm, service_radius_km: num });
                            }}
                            onBlur={(e) => {
                              let num = parseInt(e.target.value, 10);
                              if (isNaN(num) || num < 1) num = 15;
                              if (num > 150) num = 150;
                              setApplicationForm({ ...applicationForm, service_radius_km: num });
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
                          value={applicationForm.service_radius_km || 20}
                          onChange={(e) =>
                            setApplicationForm({
                              ...applicationForm,
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
                            onClick={() => setApplicationForm({ ...applicationForm, service_radius_km: km })}
                            className={`px-2 py-0.5 rounded-md text-[11px] font-semibold transition-all border ${
                              applicationForm.service_radius_km === km
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                                : 'bg-[#070b0e] text-slate-400 border-[#182836] hover:text-white'
                            }`}
                          >
                            {km} km
                          </button>
                        ))}
                      </div>

                      {applicationForm.service_radius_km >= 150 && (
                        <p className="text-[11px] text-amber-300/90 bg-amber-950/20 p-2 rounded-lg border border-amber-500/20">
                          💡 150 km é o limite regional padrão para deslocamento. Para clientes em outros estados ou remotos, marque também a opção <strong>Online / Nacional</strong>.
                        </p>
                      )}
                    </div>
                  )}
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

                {/* Indicação / Parceria de Confiança (Sem atrito e sem ruído de bonificação) */}
                {applicationForm.referred_by_code ? (
                  <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/40 flex items-center justify-between text-xs animate-in fade-in">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                      <div>
                        <span className="font-bold text-white block">Link de Parceria Reconhecido</span>
                        <span className="text-[11px] text-emerald-300 font-mono">Código: {applicationForm.referred_by_code}</span>
                      </div>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold">
                      Análise Prioritária
                    </span>
                  </div>
                ) : (
                  <div className="text-xs pt-0.5">
                    {!showManualReferralInput ? (
                      <button
                        type="button"
                        onClick={() => setShowManualReferralInput(true)}
                        className="text-[11px] text-slate-400 hover:text-amber-300 underline transition-colors"
                      >
                        Possui um código de parceiro ou convite?
                      </button>
                    ) : (
                      <div className="p-3 rounded-xl bg-[#070b0e] border border-[#182836] space-y-1.5 animate-in fade-in">
                        <label className="block text-slate-300 font-medium text-xs">Código de Parceiro (Opcional)</label>
                        <input
                          type="text"
                          placeholder="Ex: PAT-ABC123"
                          value={applicationForm.referred_by_code}
                          onChange={(e) => setApplicationForm({ ...applicationForm, referred_by_code: e.target.value.toUpperCase() })}
                          className="w-full px-3 py-2 rounded-xl bg-[#0d151c] border border-[#182836] text-white uppercase placeholder-slate-600 focus:border-amber-500 outline-none font-mono text-xs"
                        />
                      </div>
                    )}
                  </div>
                )}

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

      {/* Modal de Vagas de Emprego da Empresa */}
      <BusinessJobsModal
        business={selectedJobsBusiness}
        isOpen={Boolean(selectedJobsBusiness)}
        onClose={() => setSelectedJobsBusiness(null)}
      />

      {/* Footer */}
      <footer className="border-t border-[#182836] bg-[#070b0e] text-slate-400 text-xs py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <BrasilLogo size={20} className="w-5 h-5 !rounded-md" />
            <span>© 2026 Patriota Indica. A rede de confiança da livre iniciativa e valores tradicionais.</span>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <button onClick={() => setShowManifestoModal(true)} className="hover:text-amber-300">
              Carta de Princípios
            </button>
            <Link href="/vagas" className="text-amber-300 hover:underline flex items-center gap-1 font-semibold">
              <Briefcase className="w-3.5 h-3.5" /> Vagas de Emprego
            </Link>
            <Link href="/termos" className="hover:text-amber-300">Termos de Uso</Link>
            <Link href="/privacidade" className="hover:text-amber-300">Política de Privacidade (LGPD)</Link>
            <Link href="/painel-empresa" className="text-amber-400 font-semibold hover:underline flex items-center gap-1">
              <Store className="w-3.5 h-3.5" /> Painel da Empresa
            </Link>
            <Link href="/admin" className="text-slate-400 hover:text-white hover:underline flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Painel Admin
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
